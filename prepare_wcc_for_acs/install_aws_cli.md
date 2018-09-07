
```
mkdir /data/awscli
cd /data/awscli
curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip
unzip awscli-bundle.zip
./awscli-bundle/install -i /data/awscli/aws -b /data/awscli/bin/aws
```

run  `/data/awscli/bin/aws --version` to confirm version 