#!/usr/bin/python3.5
import asyncio
import hashlib
import json
import os

import aiohttp
import requests
import magic

from bs4 import BeautifulSoup


async def download_report(session, report):
    report_date = report['Date']
    report_title = report['Title']
    report_year = report['Year']
    report_source = report['Source']
    report_link = report['Link']
    report_filename = report['Filename']
    report_sha1 = report['SHA-1']

    # Ensure directory exists
    os.makedirs(report_year, exist_ok=True)

    # Set hash check
    hash_check = hashlib.sha1()

    # Set download path
    download_path = os.path.join(report_year, report_filename)

    # File with PDF extension path
    pdf_extension_path = download_path + ".pdf"

    if os.path.exists(download_path) or os.path.exists(pdf_extension_path):
        print("[!] File {} already exists".format(report_filename))
    else:

        try:
            # Download report preview page for parsing
            async with session.get(report_link) as splash_response:
                splash_page = await splash_response.content.read()

            # Parse preview page for desired elements to build download URL
            soup = BeautifulSoup(splash_page, 'lxml')
            sections = soup.find('body').find('script').contents[0].split(';')
            app_api = json.loads(sections[1].split('=')[1])['/app-api/enduserapp/shared-item']
            
            # Build download URL
            box_url = "https://app.box.com/index.php"
            box_args = "?rm=box_download_shared_file&shared_name={}&file_id={}"
            file_url = box_url + box_args.format(app_api['sharedName'], 'f_{}'.format(app_api['itemID']))

            # Use semaphore to limit download rate
            async with sem:
                # Download file in chunks and save to folder location
                async with session.get(file_url) as download_response:
                    with open(download_path, 'wb') as f_handle:
                        while True:
                            chunk = await download_response.content.read(1024)
                            hash_check.update(chunk)
                            if not chunk:
                                break
                            f_handle.write(chunk)
                    await download_response.release()

            # Verify file contents based on expected hash value
            if hash_check.hexdigest() != report_sha1:
                os.remove(download_path)
                raise ValueError("File integrity check failed")

            # Identify filetype and add extension if PDF
            file_type = magic.from_file(download_path, mime=True)

            if file_type == "application/pdf":
                os.rename(download_path, pdf_extension_path)

            print("[+] Successfully downloaded {}".format(report_filename))

        except Exception as unexpected_error:
            message = "[!] Download failure for {}".format(report['Filename'])
            print(message, unexpected_error)


async def download_all_reports(loop, APT_reports):
    with aiohttp.ClientSession(loop=loop) as session:
        download_queue = [loop.create_task(download_report(session, report)) for report in APT_reports]
        await asyncio.wait(download_queue)


if __name__ == '__main__':
    # Retrieve APT Note Data
    github_url = "https://raw.githubusercontent.com/aptnotes/data/master/APTnotes.json"
    APTnotes = requests.get(github_url)

    if APTnotes.status_code == 200:
        # Load APT report metadata into JSON container
        APT_reports = json.loads(APTnotes.text)

        # Reverse order of reports in order to download newest to oldest
        APT_reports.reverse()

        # Set semaphore for rate limiting
        sem = asyncio.Semaphore(10)

        # Create async loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(download_all_reports(loop, APT_reports))
