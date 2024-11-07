from django.shortcuts import render
from django.http import HttpResponse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import time

# Helper functions for scraping
def get_release_date(driver):
    R1 = '//*[@id="application"]/main/div[1]/div[3]/div[1]/div[2]/div[2]/span[1]/span'
    R2 = '//*[@id="application"]/main/div[1]/div[3]/div[1]/div[2]/div/span[1]/span'

    element_R1 = driver.find_elements(By.XPATH, R1)
    element_R2 = driver.find_elements(By.XPATH, R2)

    if element_R1:
        return element_R1[0].get_attribute('innerHTML')
    elif element_R2:
        return element_R2[0].get_attribute('innerHTML')
    else:
        return "Release Date not found"

def get_title(driver):
    titles_xpaths = [
        '//*[@id="lyrics-root"]/div[1]/div[2]/h2',
        '//*[@id="lyrics-root"]/div[1]/div/h2',
        '//*[@id="lyrics-root"]/div[1]/div/div/h2',
        '//*[@id="lyrics-root"]/div[1]/div[2]/div/h2'
    ]
    
    for xpath in titles_xpaths:
        elements = driver.find_elements(By.XPATH, xpath)
        if elements:
            return elements[0].get_attribute('innerHTML')
    
    return "Title not found"

def get_singer(driver):
    S1 = '//*[@id="application"]/main/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/span/span/a'
    S2 = '//*[@id="application"]/main/div[1]/div[3]/div[1]/div[1]/div[1]/span/span/a'

    element_S1 = driver.find_elements(By.XPATH, S1)
    element_S2 = driver.find_elements(By.XPATH, S2)

    if element_S1:
        return element_S1[0].get_attribute('innerHTML')
    elif element_S2:
        return element_S2[0].get_attribute('innerHTML')
    else:
        return "Singer name not found"

def remove_anchor_tags(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for a_tag in soup.find_all('a'):
        a_tag.unwrap()
    return str(soup)

def get_combined_lyrics(driver):
    lyrics_parts_xpaths = [
        '//*[@id="lyrics-root"]/div[2]',
        '//*[@id="lyrics-root"]/div[5]',
        '//*[@id="lyrics-root"]/div[8]',
        '//*[@id="lyrics-root"]/div[11]',
        '//*[@id="lyrics-root"]/div[14]',
        '//*[@id="lyrics-root"]/div[17]',
        '//*[@id="lyrics-root"]/div[20]',
        '//*[@id="lyrics-root"]/div[23]',
        '//*[@id="lyrics-root"]/div[26]',
        '//*[@id="lyrics-root"]/div[29]',
        '//*[@id="lyrics-root"]/div[32]',
    ]

    combined_lyrics = ''
    for xpath in lyrics_parts_xpaths:
        try:
            lyrics_part = driver.find_element(By.XPATH, xpath)
            combined_lyrics += lyrics_part.get_attribute("innerHTML")
        except NoSuchElementException:
            pass

    return remove_anchor_tags(combined_lyrics)

# Main view function
def scraper_view(request):
    if request.method == "POST":
        url = request.POST.get("url")
        num_posts_from = int(request.POST.get("num_posts_from"))
        num_posts_to = int(request.POST.get("num_posts_to"))
        file_name = request.POST.get("file_name")
        
        # Validate input
        if not url or not file_name:
            return HttpResponse("URL and file name are required.", status=400)

        data_list = []
        driver = webdriver.Chrome()  # Ensure Chromedriver is correctly installed and in PATH
        try:
            driver.get(url)
            driver.maximize_window()
            time.sleep(5)  # Allow page to load

            # Get album title
            album_title = driver.find_element(By.XPATH, '/html/body/routable-page/ng-outlet/album-page/header-with-cover-art/div/div/div[1]/div[2]/div/h1')
            album_title_innertext = album_title.get_attribute("innerHTML")

            # Iterate over the range of posts to scrape
            for num_post in range(num_posts_from, num_posts_to + 1):
                index_click = driver.find_element(By.XPATH, f'/html/body/routable-page/ng-outlet/album-page/div[2]/div[1]/div/album-tracklist-row[{num_post}]/div/div[2]/a/h3')
                ActionChains(driver).key_down(Keys.CONTROL).click(index_click).key_up(Keys.CONTROL).perform()
                
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(2)

                title_innertext = get_title(driver)
                singer_innertext = get_singer(driver)
                innertext_lyrics_combined = get_combined_lyrics(driver)
                release_date_innertext = get_release_date(driver)
                source_url = driver.current_url

                lyrics_content = f'<h2>{title_innertext}</h2> {innertext_lyrics_combined} <h4>Artist - {singer_innertext}</h4> <h4>Release Date - {release_date_innertext}</h4>'

                data_list.append({
                    "Main Title": f"{title_innertext} - {singer_innertext}",
                    "Lyrics (Content)": lyrics_content,
                    "Expert": f"{title_innertext}, {singer_innertext}",
                    "Featuring Detail": f'Artist - {singer_innertext}',
                    "Album": album_title_innertext,
                    "Release Date": release_date_innertext,
                    "Genius Link": source_url
                })

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)

            # Create DataFrame and save to Excel
            df = pd.DataFrame(data_list)
            df['Lyrics (Content)'] = df['Lyrics (Content)'].apply(lambda x: [x[i:i+32767] for i in range(0, len(x), 32767)])
            df = df.explode('Lyrics (Content)')

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{file_name}.xlsx"'
            df.to_excel(response, index=False)
            return response

        except Exception as e:
            return HttpResponse(f"Error during scraping: {e}", status=500)

        finally:
            driver.quit()

    return render(request, "index.html")
