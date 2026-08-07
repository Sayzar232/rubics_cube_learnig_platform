from selenium import webdriver
from bs4 import BeautifulSoup

def get_content(url):
    driver = webdriver.Chrome() 
    driver.get(url)
    response = driver.page_source
    driver.quit()
    with open("response.html", "w", encoding="utf-8") as f:
        f.write(response)
    return response

def save_plls(plls):
    for i in range(len(plls)):
        with open(f"frontend/public/assets/algorithms/pll-{(i + 1) if i + 1 > 9 else '0' + str(i + 1)}.svg", "w", encoding="utf-8") as f:
            f.write(plls[i].prettify())

def parse_groups(content):
    soup = BeautifulSoup(content, 'html.parser')

    groups = soup.find_all("div", class_="category-subtitle")

    groups = list(map(lambda x: x.find("a", href="#"), groups))


def parse_plls(content):
    soup = BeautifulSoup(content, 'html.parser')

    plls = soup.find_all("svg", width="75")

    print(len(plls))

    save_plls(plls)


if __name__ == "__main__":
    url = "https://speedcubedb.com/a/3x3/PLL"
    content = get_content(url)
    parse_plls(content)