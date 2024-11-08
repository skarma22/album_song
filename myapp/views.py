# scraper/views.py
from django.shortcuts import render
from django.http import JsonResponse
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import time

# Helper function to remove anchor tags from HTML content
def remove_anchor_tags(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for a_tag in soup.find_all('a'):
        a_tag.unwrap()  # Remove anchor tags while keeping inner content
    return str(soup)

# Helper function to get release date
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

# Helper function to get title
def get_title(driver):
    # XPaths for potential title elements
    T1 = '//*[@id="lyrics-root"]/div[1]/div[2]/h2'
    T2 = '//*[@id="lyrics-root"]/div[1]/div/h2'
    T3 = '//*[@id="lyrics-root"]/div[1]/div/div/h2'
    T4 = '//*[@id="lyrics-root"]/div[1]/div[2]/div/h2'
    element_T1 = driver.find_elements(By.XPATH, T1)
    element_T2 = driver.find_elements(By.XPATH, T2)
    element_T3 = driver.find_elements(By.XPATH, T3)
    element_T4 = driver.find_elements(By.XPATH, T4)
    if element_T1:
        return element_T1[0].get_attribute('innerHTML')
    elif element_T2:
        return element_T2[0].get_attribute('innerHTML')
    elif element_T3:
        return element_T3[0].get_attribute('innerHTML')
    elif element_T4:
        return element_T4[0].get_attribute('innerHTML')
    else:
        return "Title not found"

# Helper function to get singer name
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

# Helper function to get combined lyrics
def get_combined_lyrics(driver):
    lyrics_parts_xpaths = [
        '//*[@id="lyrics-root"]/div[2]',
        '//*[@id="lyrics-root"]/div[5]',
        '//*[@id="lyrics-root"]/div[8]',
        '//*[@id="lyrics-root"]/div[11]',
        '//*[@id="lyrics-root"]/div[14]',
    ]
    combined_lyrics = ''
    for xpath in lyrics_parts_xpaths:
        try:
            lyrics_part = driver.find_element(By.XPATH, xpath)
            innertext_lyrics_part = lyrics_part.get_attribute("innerHTML")
            combined_lyrics += innertext_lyrics_part
        except NoSuchElementException:
            pass
    return remove_anchor_tags(combined_lyrics)

# View to render the form template
def scrape_form(request):
    return render(request, 'index.html')

# Main view for handling scraping
def scrape_album(request):
    if request.method == "GET":
        # Retrieve form data
        url = request.GET.get("url")
        num_posts_from = int(request.GET.get("num_posts_from"))
        num_posts_to = int(request.GET.get("num_posts_to"))
        file_name = request.GET.get("file_name")

        data_list = []
        try:
            driver = webdriver.Chrome()  # Ensure ChromeDriver is installed
            driver.get(url)
            driver.maximize_window()
            time.sleep(5)

            album_title = driver.find_element(By.XPATH, '/html/body/routable-page/ng-outlet/album-page/header-with-cover-art/div/div/div[1]/div[2]/div/h1').get_attribute("innerHTML")

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

                lyrics_content = f'<h2>{title_innertext}</h2> {innertext_lyrics_combined} <h4>{"Artist - " + singer_innertext}</h4> <h4>{"Release Date on " + release_date_innertext}</h4>'

                data_list.append({
                    "Main Title": title_innertext + ' - ' + singer_innertext,
                    "Lyrics (Content)": lyrics_content,
                    "Expert": title_innertext + ', ' + singer_innertext,
                    "Featuring Detail": 'Artist - ' + singer_innertext,
                    "Album": album_title,
                    "Release Date": release_date_innertext,
                    "Genius Link": source_url
                })

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)

        finally:
            driver.quit()

        # Save data to an Excel file
        df = pd.DataFrame(data_list)
        df['Lyrics (Content)'] = df['Lyrics (Content)'].apply(lambda x: [x[i:i+32767] for i in range(0, len(x), 32767)])
        df = df.explode('Lyrics (Content)')
        df.to_excel(f'{file_name}.xlsx', index=False)

        # Send success response
        return JsonResponse({"message": f"Scraping completed and data saved to {file_name}.xlsx"}, status=200)
