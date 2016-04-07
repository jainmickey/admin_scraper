import config
import json
import requests
from bs4 import BeautifulSoup


def get_page_links(bs4_parsed_content):
    theaders = bs4_parsed_content.find(id="content-main").find_all("th")
    all_links = [head.find("a") for head in theaders]
    valid_links = [link for link in all_links
                   if link and link.get('href')[0] == '/']
    return valid_links


def get_parsed_content_from_link(session, headers, link):
    response = session.get(config.base_url+link, headers=headers,
                           cookies=dict(session.cookies))
    if response.status_code == 200:
        return BeautifulSoup(response.content, "html.parser")
    return None


def get_form_data(session, headers, link):
    page = get_parsed_content_from_link(session, headers, link)
    values = {'id': link.split('/')[-2]}
    fields = page.find_all("div", class_="form-row")
    for field in fields:
        label = field.find("label")
        val = field.find(id=label['for'])
        values[label.get_text()] = ''
        value = ''
        if str(val.name) == 'select':
            val = val.find('option', selected=True)
            if val:
                value = {'id': val.get("value"), "name": val.get_text()}
        else:
            if val:
                value = val.get("value") if val.get("value") else val.get_text()

        values[label.get_text()] = value
    print("Values", values)
    return values


def get_all_links_pages(session, headers):
    home_page = get_parsed_content_from_link(session, headers, config.admin_url)
    all_links = get_page_links(home_page)
    page_wise_links = dict()
    for link in all_links:
        page = get_parsed_content_from_link(session, headers, link.get('href'))
        paginator = page.find(id="content-main").find(class_="paginator")
        page_wise_links[link.get_text()] = get_page_links(page)
        if paginator and paginator.find_all("a"):
            try:
                num_pages = int(paginator.find_all("a")[-1].get("href").split("p=")[-1])
            except ValueError:
                num_pages = 0
            for page_num in range(1, num_pages + 1):
                new_page = get_parsed_content_from_link(session, headers, link.get('href')+'?p={}'.format(page_num))
                page_wise_links[link.get_text()].extend(get_page_links(new_page))

    for key in page_wise_links.keys():
        data = list()
        for link in page_wise_links.get(key):
            data.append({link.get_text(): get_form_data(session, headers, link.get("href"))})
        with open('{}.txt'.format(key), 'w') as outfile:
            json.dump(data, outfile)


def get_logged_in_session():
    s = requests.Session()
    s.get(config.base_url+config.login_url)
    token = s.cookies['csrftoken']
    login_data = dict(username=config.username, password=config.password, csrfmiddlewaretoken=token)
    headers = {"X-CSRFToken": token}
    s.post(config.base_url+config.login_url, data=login_data, headers=headers, cookies=dict(s.cookies))
    return {'session': s, 'headers': headers, 'token': token}


if __name__ == '__main__':
    session_data = get_logged_in_session()
    get_all_links_pages(session_data.get('session'), session_data.get('headers'))
