#!/usr/bin/python3
import os
import hashlib
import json
import requests
import magic
from bs4 import BeautifulSoup

github_url = "https://raw.githubusercontent.com/aptnotes/data/master/APTnotes.json"
APTnotes = requests.get(github_url)

if APTnotes.status_code == 200:
    # Load APT report metadata into JSON container
    APT_reports = json.loads(APTnotes.text)

    # Process each report based on obtained metadata
    for report in APT_reports:
        report_date = report['Date']
        report_title = report['Title']
        report_year = report['Year']
        report_source = report['Source']
        report_link = report['Link']
        report_filename = report['Filename']
        report_sha1 = report['SHA-1']

        try:
            # Download Box Splash/Preview page for file
            report_splash = requests.get(report_link)

            # Parse preview page for desired elements to build download URL
            soup = BeautifulSoup(report_splash.text, 'lxml')
            sections = soup.find('body').find('script').contents[0].split(';')
            app_api = json.loads(sections[1].split('=')[1])['/app-api/enduserapp/shared-item']
            
            # Build download URL
            box_url = "https://app.box.com/index.php"
            box_args = "?rm=box_download_shared_file&shared_name={}&file_id={}"
            file_url = box_url + box_args.format(app_api['sharedName'], 'f_{}'.format(app_api['itemID']))

            # Ensure directory exists
            os.makedirs(report_year, exist_ok=True)

            # Set hash check
            hash_check = hashlib.sha1()

            # Set download path
            download_path = os.path.join(report_year, report_filename)

            # File with PDF extension path
            pdf_extension_path = download_path + ".pdf"

            if os.path.exists(download_path) or os.path.exists(pdf_extension_path):
                print("[+] File {} already exists".format(report_filename))
                continue
            else:
                # Stream download the file
                report_file = requests.get(file_url, stream=True)

                # Download file to desired path in chunks
                with open(download_path, 'wb') as f:

                    for chunk in report_file.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            hash_check.update(chunk)

                # Verify file contents based on expected hash value
                if hash_check.hexdigest() != report_sha1:
                    os.remove(download_path)
                    raise ValueError("File integrity check failed")

        except Exception as unexpected_error:
            message = "[!] Download failure for {}".format(report_filename)
            print(message, unexpected_error)

        else:
            # Identify filetype and add extension if PDF
            file_type = magic.from_file(download_path, mime=True)

            if file_type == "application/pdf":
                os.rename(download_path, pdf_extension_path)

            message = "[+] Successfully downloaded {}".format(report_filename)
            print(message)
