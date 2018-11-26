#!/usr/bin/python
#
# example:
# ./migrate.py -pMyProfile -i/var/data/archives/test/18-oct-30_09.28.23_669_07 -o/myhomedir/data/test-data -s/myhomedir/sample-files
#


import argparse
import csv
import logging
import os
import time
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

import yaml

import util

import cPickle as pickle

# script version and run time
__version__ = '1.0'
scriptVersionAndRunTime = __version__ + ' ' + str(datetime.now())

# need to count across .hda files
name_field_value_count = {}

class InvalidDocument(Exception):
    def __init__(self,field_name, field_type, field_value, document_id):
        self.field_name = field_name
        self.field_type = field_type
        self.field_value = field_value
        self.document_id = document_id

    def get_error_message(self):
        return "Invalid Type - Field '"+self.field_name+"' expected type: '" + self.field_type + "', received value: '" + self.field_value + "' for document: " + self.document_id


class WccDateFormatError(Exception):
    def __init__(self, bl_date_format):
        self.bl_date_format = bl_date_format

    def __str__(self):
        return repr(self.bl_date_format)


class ContentModelDefinition:
    def __init__(self, profile, fields, aspects, content_type):
        self.profile = profile
        self.fields = fields
        self.aspects = aspects
        self.content_type = content_type


class SampleFiles:
    def __init__(self, dirpath):
        self.ext_to_path = {}
        for f in os.listdir(dirpath):
            path_parts = os.path.splitext(f)
            if len(path_parts) >= 2:
                ext = path_parts[-1]
                fullpath = dirpath+'/'+f
                if ext in self.ext_to_path:
                    self.ext_to_path[ext].append(fullpath)
                else:
                    self.ext_to_path[ext] = [fullpath]

    def get(self, ext, idx=0):
        if ext in self.ext_to_path:
            l = len(self.ext_to_path[ext])
            return self.ext_to_path[ext][idx % l]
        else:
            return None

class WebcenterData:
    BL_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    def __init__(self, content_model_definition, basedir,  number_of_data_rows, number_of_fields,
                 bl_field_types):
        self.content_model_definition = content_model_definition
        self.basedir = basedir
        self.number_of_data_rows = int(number_of_data_rows)
        self.number_of_fields = int(number_of_fields)
        self.data_rows = []
        self.field_names = []
        self.bl_field_types = [field.split(' ')[0] for field in bl_field_types.split(
            ',')]  # convert string of "'<fieldName> <fieldType>','<fieldName> <fieldType>'..." into an array of <fieldName>

    def add_field(self, line):
        wcc_field_name = line.split(' ')[
            0].rstrip()  # convert string of "'<fieldName> <number> <number>' into <fieldName>
        self.field_names.append(wcc_field_name)

    def add_data_row(self, data_row):
        self.data_rows.append(data_row)

    # convert all date fields into date objects
    def convert_dates(self):
        for i in range(0, len(self.field_names)):
            if self.field_names[i] in self.bl_field_types:
                for j in range(0, self.number_of_data_rows):
                    if self.data_rows[j][i] != '':
                        date_field = self.data_rows[j][i].split('\'')[1]
                        d = datetime.strptime(date_field, self.BL_DATE_FORMAT)
                        self.data_rows[j][i] = d

    def write_csv(self, csv_file):
        logging.info('writing to csv: ' + csv_file)
        with open(csv_file, 'w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(self.field_names)
            writer.writerows(self.data_rows)

class HdaParser:
    EXPECTED_BL_DATE_FORMAT = "'{ts' ''yyyy-MM-dd HH:mm:ss{.SSS}[Z]'''}'!tAmerica/Los_Angeles"

    def __init__(self, content_model_definition):
        self.content_model_definition = content_model_definition
        self.bl_field_types = None
        self.number_of_rows = 0

    def parse_metadata(self, input, number_to_process):
        process_all_documents = (number_to_process is None)

        # primary_file in hda files uses relative path. Need to prepend basedir, which
        # is the grand parent of the hda file
        path_parts = input.split('/')
        basedir = os.path.join(os.sep, *path_parts[:-2])
        batchId = path_parts[-2]
        with open(input, 'r') as f:
            # File metadata
            while True:
                line = f.readline()
                file_metadata_finished = self.__parse_file_metadata(line)
                if file_metadata_finished:
                    break

            # number of fields
            num_of_fields = f.readline()

            if not process_all_documents:
                self.number_of_rows = number_to_process
            wcc_data = WebcenterData(self.content_model_definition, basedir, self.number_of_rows,
                                     num_of_fields, self.bl_field_types)

            # Field Names
            for i in range(0, wcc_data.number_of_fields):
                line = f.readline()
                wcc_data.add_field(line)
            wcc_data.field_names.append('wccArchiverBatchId')
            wcc_data.field_names.append('scriptVersionAndRunTime')

            # metadata
            for n in range(0, self.number_of_rows):
                data_row = []
                for j in range(0, wcc_data.number_of_fields):
                    line = f.readline()
                    data_row.append(line.rstrip())
                data_row.append(batchId)
                data_row.append(scriptVersionAndRunTime)
                wcc_data.add_data_row(data_row)

            if process_all_documents:
                self.__validate_end_of_file(f.readline())

            return wcc_data

    def __parse_file_metadata(self, line):
        logging.debug("line: " + line)

        if line.startswith('@ResultSet ExportResults'):  # Last line of 'file metadata'
            return True
        if line.startswith("blFieldTypes="):
            self.bl_field_types = line[13:].rstrip()
        if line.startswith("blDateFormat="):
            found_date_format = line[13:].rstrip()
            if found_date_format != self.EXPECTED_BL_DATE_FORMAT:  # validate date format is as expected
                raise WccDateFormatError(line)
        if line.startswith('NumRows='):
            self.number_of_rows = int(line[8:])

        return False

    def __validate_end_of_file(self, line):
        if line.rstrip() != "@end":
            raise Exception("Invalid File expected '@end' found '" + line + "'")


class WccXmlWriter:
    def __init__(self, wcc_data, should_validate_field_value, sample_files):
        self.wcc_data = wcc_data
        self.primary_file_field_index = self.wcc_data.field_names.index('primaryFile')
        self.should_validate_field_value = should_validate_field_value
        self.sample_files = sample_files

    def write_xml_files(self, output, print_to_screen):
        for i in range(0, self.wcc_data.number_of_data_rows):
            try:
                xml_doc = self.__create_xml(i)
                primary_file_name = self.__get_primary_file_name(i)
                file_ext = self.__get_primary_file_ext(i)
                self.__print_xml_to_screen(xml_doc, print_to_screen)
                if self.sample_files:
                    if self.sample_files.get(file_ext, i):
                        self.__write_xml_file(xml_doc, primary_file_name, output)
                        self.__link_content_file(primary_file_name, file_ext, output, i)
                    else:
                        logging.warning("  missing ext " + file_ext + " in sample files")
                else:
                    primary_file = self.wcc_data.data_rows[i][self.primary_file_field_index]
                    self.__write_xml_file(xml_doc, primary_file_name, output)
                    self.__link_content_file(primary_file_name, file_ext, output, i)

            except InvalidDocument as error:
                #if there is an invalid document, don't write the file and just return an error message
                logging.error(error.get_error_message())

    def __get_primary_file_name(self, document_index):
        primary_file = self.wcc_data.data_rows[document_index][self.primary_file_field_index]
        primary_file_name = os.path.basename(primary_file)
        return primary_file_name

    def __get_primary_file_ext(self, document_index):
        file_ext = ''
        primary_file_name = self.__get_primary_file_name(document_index)
        file_name_parts = os.path.splitext(primary_file_name)
        if len(file_name_parts) >= 2:
           file_ext = file_name_parts[1]

        return file_ext

    def __link_content_file(self, primary_file_name, file_ext, xml_file_output_dir, idx=0):
        primary_file = os.path.join(self.wcc_data.basedir, self.wcc_data.data_rows[idx][self.primary_file_field_index])
        srcfile = self.sample_files.get(file_ext, idx) if self.sample_files else primary_file
        dest = os.path.join(xml_file_output_dir, primary_file_name)
        if not os.path.exists(dest):
            os.system('ln -s ' + srcfile + ' ' +  dest)  # os.symlink does not work with '@' in path

    def __write_xml_file(self, xml_doc, primary_file_name, xml_file_output_dir):
        def append_doc_type(xml_file):  # ElemenTree is unable to add DOCTYPE
            with open(xml_file, 'r') as f:
                content = f.readlines()

            final_content = content[:1]
            final_content.append(
                '<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">')
            final_content.extend(content[1:])

            with open(xml_file, 'w') as f:
                f.writelines(final_content)

        util.make_dirs(xml_file_output_dir)

        xml_file_name = primary_file_name + ".metadata.properties.xml"
        xml_file = os.path.join(xml_file_output_dir, xml_file_name)
        logging.debug('  writing to xml: ' + xml_file)

        # xml_declaration=True is not supported by python 2.6.6 on uwctprod01
        ElementTree.ElementTree(xml_doc).write(xml_file, encoding='UTF-8')
        append_doc_type(xml_file)

    def __print_xml_to_screen(self, xml_doc, print_to_screen):
        if print_to_screen:
            print self.__prettify_xml(xml_doc)

    def __create_xml(self, document_index):
        def add_content_type(document):
            child = SubElement(document, 'entry', {'key': 'type'})
            child.text = self.wcc_data.content_model_definition.content_type

        def add_aspects(document):
            if len(self.wcc_data.content_model_definition.aspects) > 0:
                child = SubElement(document, 'entry', {'key': 'aspects'})
                aspects = ','.join(self.wcc_data.content_model_definition.aspects)
                child.text = aspects

        def add_fields(document):
            primary_file_name = self.__get_primary_file_name(document_index)
            file_name_parts = os.path.splitext(primary_file_name)
            file_ext = file_name_parts[1] if len(file_name_parts) >= 2 else ''
            for field in self.wcc_data.content_model_definition.fields:
                source_field = field['source_field']
                field_type = field['type'] if 'type' in field else 'text'
                field_name = field['name']
                field_index = self.wcc_data.field_names.index(source_field)
                field_value = self.wcc_data.data_rows[document_index][field_index]

                if self.should_validate_field_value:
                    validate_field_value(field_name, field_type, field_value)

                if field_type == 'date' and field_value != '':
                    field_value = field_value.isoformat()

                if field_name == 'cm:name':
                    if field_value.find('.') < 0:
                        field_value += file_ext

                    if field_value in name_field_value_count:
                        file_name_parts = os.path.splitext(field_value)
                        name_field_value_count[field_value] += 1
                        field_value = file_name_parts[0] + '(' + str(name_field_value_count[field_value] - 1) + ')' + file_name_parts[-1]
                    else:
                        name_field_value_count[field_value] = 1

                if (field_type == 'date' or field_type == 'int') and field_value == '':
                    pass  # Don't write date or int fields if they don't have values
                else:
                    key = field['name']
                    child = SubElement(document, 'entry', {'key': key})
                    child.text = field_value


        def validate_field_value(field_name, field_type, field_value):
            document_id = self.wcc_data.data_rows[document_index][0]

            if field_type == 'int':
                if field_value != '':
                    try:
                        value = int(field_value)
                    except ValueError:
                        raise InvalidDocument(field_name, field_type, field_value, document_id)
            if field_type == 'date':
                if field_value != '':
                    try:
                        value = field_value.isoformat()
                    except AttributeError:
                        raise InvalidDocument(field_name, field_type, field_value, document_id)


        xml_doc = Element('properties')
        add_content_type(xml_doc)
        add_aspects(xml_doc)
        add_fields(xml_doc)

        return xml_doc

    def __prettify_xml(self, elem):
        rough_string = ElementTree.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


class HdaTranslator:
    def __init__(self, content_model_definition_file, content_model_profile, csv_file,
                 wcc_archives_input_dir, number_of_docs_to_process, print_to_screen, output_directory,
                 should_validate_field_value, seq1, seq2, countFile, sample_files_dir=None):
        self.content_model_definition_file = content_model_definition_file
        self.content_model_profile = content_model_profile
        self.csv_file = csv_file
        self.wcc_archives_input_dir = wcc_archives_input_dir
        self.number_of_docs_to_process = number_of_docs_to_process
        self.print_to_screen = print_to_screen
        self.output_directory = output_directory
        self.should_validate_field_value = should_validate_field_value
        self.seq1 = seq1
        self.seq2 = seq2
        self.countFile = countFile

        self.sample_files = SampleFiles(sample_files_dir) if sample_files_dir else None

    def process_one_hda_file(self, parser, hda_input_file, output_directory):
        start_time = time.time()

        # Translate Results
        wcc_data = parser.parse_metadata(hda_input_file, self.number_of_docs_to_process)
        wcc_data.convert_dates()

        logging.info('Processing ' + hda_input_file)
        logging.info('  number of data rows: ' + str(wcc_data.number_of_data_rows))
        logging.info('  output directory: ' + output_directory)

        if self.csv_file:
            wcc_data.write_csv(self.csv_file)

        if output_directory:
            wcc_xml_writer = WccXmlWriter(wcc_data, self.should_validate_field_value, self.sample_files)
            wcc_xml_writer.write_xml_files(output_directory, self.print_to_screen)

        end_time = time.time()
        logging.info('  duration: ' + str(end_time - start_time) + ' seconds')

    def run(self):
        # Load Content Model
        content_model_definition = self.__load_content_model(self.content_model_definition_file,
                                                             self.content_model_profile)
        # Parse HDA File
        parser = HdaParser(content_model_definition)

        # nested function used to sort files on sequence number
        def take_seq(f):
            if f.endswith('.hda') and f != 'docmetadefinition.hda':
                seqno = f.split('~')[1].split('.')[0]
                return int(seqno)
            else:
                return -1

        count_file_dir = self.output_directory + '/count_files'
        if not os.path.exists(count_file_dir):
            os.makedirs(count_file_dir)

        prev_count_file = self.countFile
        global name_field_value_count
        for f in sorted(os.listdir(self.wcc_archives_input_dir), key=take_seq):
            if f.endswith('.hda') and f != 'docmetadefinition.hda':
                iSeqno = take_seq(f)
                count_file = count_file_dir + '/' + f + '.count'
                if iSeqno < self.seq1 or (self.seq2 > 0 and iSeqno > self.seq2):
                    prev_count_file = count_file
                    continue

                inputFile = self.wcc_archives_input_dir+ '/' + f
                output = self.output_directory + '/' + str(iSeqno)

                if prev_count_file and os.path.isfile(prev_count_file):
                    with open(prev_count_file, 'rb') as handle:
                        name_field_value_count = pickle.load(handle)

                if not os.path.exists(output):
                    os.makedirs(output)

                self.process_one_hda_file(parser, inputFile, output)

                # save count file for use by next .hda file
                with open(count_file, 'wb') as handle:
                    pickle.dump(name_field_value_count, handle, protocol=pickle.HIGHEST_PROTOCOL)
                prev_count_file = count_file

    # derive wcc field name from from acs field name, if wcc field name is not specified
    def __get_fields(self, rawfields):
        processed_fields = []
        for f in rawfields:
            if not 'source_field' in f:
                # derive source_field name
                field_name = f['name']
                idx = field_name.find(':')
                if idx >= 0:
                    field_name = f['name'][idx+1:]
                if field_name.endswith('Id'):
                    name_len = len(field_name)
                    field_name = field_name[:name_len-1] + 'D'
                f['source_field'] = 'xuw' + field_name[0].upper() + field_name[1:]
            processed_fields.append(f)
        return processed_fields

    def __load_content_model(self, file_name, profile_name):
        content_model_definition = None
        with open(file_name, 'r') as file:
            content_model_yml = yaml.load(file)

            # common section
            common_section = content_model_yml['common']
            common_aspects = common_section['aspects']
            common_fields = self.__get_fields(common_section['fields'])
            record_fields = self.__get_fields(common_section['record_fields'])

            content_models = content_model_yml['content_models']
            for content_model in content_models:
                profile = content_model['profile']
                if profile_name == profile:
                    content_type = content_model['content_type']
                    fields = self.__get_fields(content_model['fields'])
                    fields.extend(common_fields)
                    aspects = common_aspects
                    if 'aspects' in content_model:
                        aspects.extend(content_model['aspects'])

                    if 'uw:record' in aspects:
                        fields.extend(record_fields)

                    content_model_definition = ContentModelDefinition(profile, fields, aspects,
                                                                      content_type)

        if content_model_definition is None:
            raise Exception("Invalid profile '" + profile_name + "' for file '" + file_name + "'")
        return content_model_definition


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='The input directory', required=True)
    parser.add_argument('--csv', help='An optional csv file for output of all the migrated data')
    parser.add_argument('--printToScreen', help='Print output xml to screen', action='store_true')
    parser.add_argument('-o', '--output', help='The output directory for xml files', required=True)
    parser.add_argument('-n', '--numberToProcess',
                        help='The number of documents to process, defaults to all',
                        type=int)
    parser.add_argument('-m', '--contentModelDefinition',
                        help='The definition of the content model', default='migration_content_models.yml')
    parser.add_argument('-p', '--profile',
                        help='The profile to load from the content model definition', required=True)
    parser.add_argument('-s', '--sampleFilesDir',
                        help='The sample files directory')
    parser.add_argument('--seq1', type=int, default=1, help='starting sequence number')
    parser.add_argument('--seq2', type=int, default=-1, help='ending sequence number')
    parser.add_argument('-c', '--countFile', help='name_field_value_count file to use for sequence 1')
    parser.add_argument('--validate', help='Validate data based on field type, and print to screen',
                        action='store_true')
    return parser.parse_args()


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)


def main():
    args = parse_arguments()
    configure_logging()

    logging.info('Content Profile: ' + args.profile)
    logging.info('Input directory: ' + args.input)
    logging.info('Base output directory: ' + args.output)

    # we probably should pass args, as the list becomes long
    translator = HdaTranslator(args.contentModelDefinition,
                               args.profile,
                               args.csv,
                               args.input,
                               args.numberToProcess,
                               args.printToScreen,
                               args.output,
                               args.validate,
                               args.seq1,
                               args.seq2,
                               args.countFile,
                               args.sampleFilesDir)
    start_time = time.time()

    translator.run()

    end_time = time.time()
    logging.info('Translation time: ' + str(end_time - start_time) + " seconds")


if __name__ == "__main__":
    main()
