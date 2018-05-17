#!/usr/bin/python

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


class WebcenterData:
    BL_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

    def __init__(self, content_model_definition, number_of_data_rows, number_of_fields,
                 bl_field_types):
        self.content_model_definition = content_model_definition
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
        if process_all_documents:
            logging.info("Processing all documents from file: " + input)
        else:
            logging.info("Processing " + str(number_to_process) + "documents from file: " + input)

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
            wcc_data = WebcenterData(self.content_model_definition, self.number_of_rows,
                                     num_of_fields, self.bl_field_types)

            # Field Names
            for i in range(0, wcc_data.number_of_fields):
                line = f.readline()
                wcc_data.add_field(line)

            # metadata
            for n in range(0, self.number_of_rows):
                data_row = []
                for j in range(0, wcc_data.number_of_fields):
                    line = f.readline()
                    data_row.append(line.rstrip())
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
    def __init__(self, wcc_data):
        self.wcc_data = wcc_data
        self.primary_file_field_index = self.wcc_data.field_names.index('primaryFile')

    def write_xml_files(self, output, print_to_screen):
        logging.info('writing xml to: ' + output)

        for i in range(0, self.wcc_data.number_of_data_rows):
            xml_doc = self.__create_xml(i)
            primary_file_name = self.__get_primary_file_name(i)
            self.__print_xml_to_screen(xml_doc, print_to_screen)
            self.__write_xml_file(xml_doc, primary_file_name, output)

    def __get_primary_file_name(self, document_index):
        primary_file = self.wcc_data.data_rows[document_index][self.primary_file_field_index]
        primary_file_name = os.path.basename(primary_file)
        return primary_file_name

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
        logging.debug('writing to xml: ' + xml_file)

        ElementTree.ElementTree(xml_doc).write(xml_file, encoding='UTF-8', xml_declaration=True)
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
            for field in self.wcc_data.content_model_definition.fields:
                source_field = field['source_field']
                field_index = self.wcc_data.field_names.index(source_field)
                field_value = self.wcc_data.data_rows[document_index][field_index]

                if field['type'] == 'date' and field_value != '':
                    field_value = field_value.isoformat()

                key = field['prefix'] + ':' + field['name']
                child = SubElement(document, 'entry', {'key': key})
                child.text = field_value

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
                 hda_input_file, number_of_docs_to_process, print_to_screen, xml_output_directory):
        self.content_model_definition_file = content_model_definition_file
        self.content_model_profile = content_model_profile
        self.csv_file = csv_file
        self.hda_input_file = hda_input_file
        self.number_of_docs_to_process = number_of_docs_to_process
        self.print_to_screen = print_to_screen
        self.xml_output_directory = xml_output_directory

    def run(self):
        # Load Content Model
        content_model_definition = self.__load_content_model(self.content_model_definition_file,
                                                             self.content_model_profile)
        # Parse HDA File
        parser = HdaParser(content_model_definition)

        # Translate Results
        wcc_data = parser.parse_metadata(self.hda_input_file, self.number_of_docs_to_process)
        wcc_data.convert_dates()

        logging.info('Content Profile: ' + wcc_data.content_model_definition.profile)
        logging.info('Number of data rows: ' + str(wcc_data.number_of_data_rows))

        if self.csv_file:
            wcc_data.write_csv(self.csv_file)

        if self.xml_output_directory:
            wcc_xml_writer = WccXmlWriter(wcc_data)
            wcc_xml_writer.write_xml_files(self.xml_output_directory, self.print_to_screen)

    def __load_content_model(self, file_name, profile_name):
        content_model_definition = None
        with open(file_name, 'r') as file:
            content_model_yml = yaml.load(file)
            content_models = content_model_yml['content_models']
            for content_model in content_models:
                profile = content_model['profile']
                if profile_name == profile:
                    content_type = content_model['content_type']
                    fields = [field for field in content_model['fields']]
                    aspects = content_model['aspects']
                    content_model_definition = ContentModelDefinition(profile, fields, aspects,
                                                                      content_type)

        if content_model_definition is None:
            raise Exception("Invalid profile '" + profile_name + "' for file '" + file_name + "'")
        return content_model_definition


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='The input .hda file', required=True)
    parser.add_argument('--csv', help='An optional csv file for output of all the migrated data')
    parser.add_argument('--printToScreen', help='Print output xml to screen', action='store_true')
    parser.add_argument('-o', '--output', help='The output directory for xml files', required=True)
    parser.add_argument('-n', '--numberToProcess',
                        help='The number of documents to process, defaults to all',
                        type=int)
    parser.add_argument('-m', '--contentModelDefinition',
                        help='The definition of the content model', required=True)
    parser.add_argument('-p', '--profile',
                        help='The profile to load from the content model definition', required=True)
    return parser.parse_args()


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)


def main():
    args = parse_arguments()
    configure_logging()

    translator = HdaTranslator(args.contentModelDefinition,
                               args.profile,
                               args.csv,
                               args.input,
                               args.numberToProcess,
                               args.printToScreen,
                               args.output)
    start_time = time.time()

    translator.run()

    end_time = time.time()
    logging.info('Translation time: ' + str(end_time - start_time))


if __name__ == "__main__":
    main()
