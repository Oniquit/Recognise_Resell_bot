import time
import undetected_chromedriver as uc
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from seleniumbase import BaseCase
from seleniumbase import Driver
from loguru import logger

driver = Driver(uc=True)

class AvitoParse:
    def __init__(self, 
                 url: str, 
                 keywords_list: list, 
                 count:int=10, 
                 ):
        self.url = url
        self.keywords_list = keywords_list
        self.count = count
        self.driver = Driver(uc=True)

    def __set_up_and_pass_anibot(self):
        self.driver.uc_open_with_reconnect(self.url, reconnect_time=4)
        self.driver.uc_gui_click_captcha()

    def __parser_of_pages(self):
        product_data = {
            "Product Names": [],
            "Product URLs": [],
            "Product Prices": [],
        }
        product_names = self.driver.find_elements(By.CSS_SELECTOR, "[itemprop='name']")
        
        for product in product_names:
            product_data["Product Names"].append(product.text)
        
        product_links = self.driver.find_elements(By.CSS_SELECTOR, "[itemprop='url']")
    
        for links in product_links:
            product_data["Product URLs"].append(links.get_attribute("href"))

        product_prices = self.driver.find_elements(By.CSS_SELECTOR, "[itemprop='price']")
        
        for prices in product_prices:
            product_data["Product Prices"].append(prices.get_attribute("content"))
        
        print(product_data)
    def __paginator(self):
        pass
    
    def parse(self):
        self.__set_up_and_pass_anibot()
        self.__parser_of_pages()

if __name__=="__main__":
    AvitoParse(url=input(),
               keywords_list=['minifigures', ],
               count=1,
               ).parse()