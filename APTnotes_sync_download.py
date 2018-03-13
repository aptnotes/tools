#!/usr/bin/python3
import os
import hashlib
import json
import requests

from utilities import get_download_url, load_notes, report_already_downloaded, verify_report_filetype


if __name__ == '__main__':
    # Load APT report metadata into JSON container
    APT_reports = load_notes()

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
            report_splash = requests.get(report_link).text
            file_url = get_download_url(report_splash)

            # Ensure directory exists
            os.makedirs(report_year, exist_ok=True)

            # Set hash check
            hash_check = hashlib.sha1()

            # Set download path
            download_path = os.path.join(report_year, report_filename)

            if report_already_downloaded(download_path):
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
            # Verify report filetype and add extension
            download_path = verify_report_filetype(download_path)
            print("[+] Successfully downloaded {}".format(download_path))
