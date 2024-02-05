import os
import sys

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.append(os.getcwd())
from utils import ( # noqa
    check_date,
    check_for_duplicate_amr_hash,
    create_database_session,
    generate_md5_hash,
    get_env_variables,
    initialize_webdriver,
    insert_to_amr_database,
    parse_date,
)

script_path = os.path.abspath(__file__)
script_directory = os.path.dirname(script_path)
env_path = os.path.join(script_directory, ".env")
[
    ecgains,
    _,
    base_url,
    executable_path,
    _,
    _,
    _,
    browser_type,
    smi_data_url,
    _,
    _,
    _,
    _,
    _
] = get_env_variables(env_path=env_path)

driver = initialize_webdriver(
    exec_path=executable_path,
    browser_type=browser_type,
    download_dir=None,
    is_headless=True,
)

db_session = create_database_session(database_url=smi_data_url)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299'
}

requests_session = requests.Session()
response = requests_session.get(base_url, headers=headers)

html_file_path = os.path.join(script_directory, "index.html")
with open(html_file_path, "wb") as f:
    f.write(response.content)

driver.get("file://" + html_file_path)

wait = WebDriverWait(driver, 30)

try:
    tbody_element = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "views-table"))
    ).find_element(By.TAG_NAME, "tbody")

    bid_elements = tbody_element.find_elements(By.XPATH, "./*")

    for index, bid_element in enumerate(bid_elements, start=1):
        bid_due_date = bid_element.find_element(By.XPATH, ".//td[4]/span").text
        parsed_due_date = parse_date(date=bid_due_date)
        if check_date(date=parsed_due_date):
            continue
        
        title_element = bid_element.find_element(By.XPATH, ".//td[1]/a")

        bid_title = title_element.text
        current_url = title_element.get_attribute("href")

        # BID NO + TITLE + DUE DATE
        hash = generate_md5_hash(ecgain=bid_title, bidno=bid_title, filename=parsed_due_date)

        if check_for_duplicate_amr_hash(session=db_session, hash=hash):
            continue
        
        insert_to_amr_database(
            session=db_session,
            ecgain=ecgains,
            number=bid_title,
            title=bid_title,
            due_date=parsed_due_date,
            hash=hash,
            url1=base_url,
            url2=current_url,
            description=bid_title,
        )
except Exception as e:
    print("[-] Exception thrown!")
    print(e)

driver.quit()
os.remove(html_file_path)
print("[+] End of script!")