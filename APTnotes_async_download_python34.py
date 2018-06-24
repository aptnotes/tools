#!/usr/bin/python3.4
import asyncio
import hashlib
import json
import os
import sys
import aiohttp

from utilities import get_download_url, load_notes, report_already_downloaded, verify_report_filetype


if sys.version_info.major < 3:
    raise Exception("Must be using Python 3.4")

if sys.version_info.minor < 4:
    raise Exception("Must be using Python 3.4")
    
if sys.version_info.minor > 4:
    raise Exception("Must be using Python 3.4")


@asyncio.coroutine
def fetch_report_content(session, file_url, download_path, checksum):

    # Set hash check
    hash_check = hashlib.sha1()

    download_response = yield from session.get(file_url)

    try:
        with open(download_path, 'wb') as f_handle:
            while True:
                chunk = yield from download_response.content.read(1024)
                hash_check.update(chunk)
                if not chunk:
                    break
                f_handle.write(chunk)

        # Verify file contents based on expected checksum value
        if hash_check.hexdigest() != checksum:
            os.remove(download_path)
            raise ValueError("File integrity check failed")

    except Exception as unexpected_error:
        message = "[!] Download failure for {}".format(file_url)
        print(message, unexpected_error)
        download_response.close()

    else:
        # Verify report filetype and add extension
        download_path = verify_report_filetype(download_path)
        print("[+] Successfully downloaded {}".format(download_path))
        return download_path

    finally:
        yield from download_response.release()


@asyncio.coroutine
def fetch_report_url(session, report_link):

    # Download report preview page for parsing
    splash_response = yield from session.get(report_link)

    try:
        splash_page = yield from splash_response.content.read()
        file_url = get_download_url(splash_page)

    except Exception as unexpected_error:
        message = "[!] Splash page retrieval failure for {}".format(report_link)
        print(message, unexpected_error)
        splash_response.close()

    else:
        return file_url

    finally:
        yield from splash_response.release()


@asyncio.coroutine
def download_report(session, report):
    report_date = report['Date']
    report_title = report['Title']
    report_year = report['Year']
    report_source = report['Source']
    report_link = report['Link']
    report_filename = report['Filename']
    report_sha1 = report['SHA-1']

    # Ensure directory exists
    os.makedirs(report_year, exist_ok=True)

    # Set download path
    download_path = os.path.join(report_year, report_filename)

    if report_already_downloaded(download_path):
        print("[!] File {} already exists".format(report_filename))
    else:
        file_url = yield from fetch_report_url(session, report_link)
        report_path = yield from fetch_report_content(session, file_url, download_path, report_sha1)


@asyncio.coroutine
def download_all_reports(loop, APT_reports):
    with aiohttp.ClientSession(loop=loop) as session:
        download_queue = [loop.create_task(download_report(session, report)) for report in APT_reports]
        yield from asyncio.wait(download_queue)


if __name__ == '__main__':
    # Retrieve APT Note Data
    APT_reports = load_notes()

    # Set semaphore for rate limiting
    sem = asyncio.Semaphore(10)

    # Create async loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(download_all_reports(loop, APT_reports))
