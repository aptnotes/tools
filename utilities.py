import json
from bs4 import BeautifulSoup


def get_download_url(page):
    # Parse preview page for desired elements to build download URL
    soup = BeautifulSoup(page, 'lxml')
    scripts = soup.find('body').find_all('script')
    sections = scripts[-1].contents[0].split(';')
    app_api = json.loads(sections[0].split('=')[1])['/app-api/enduserapp/shared-item']

    # Build download URL
    box_url = "https://app.box.com/index.php"
    box_args = "?rm=box_download_shared_file&shared_name={}&file_id={}"
    file_url = box_url + box_args.format(app_api['sharedName'], 'f_{}'.format(app_api['itemID']))

    return file_url
