from bs4 import BeautifulSoup

from selenium.webdriver.chrome.service import Service
from selenium import webdriver

from datetime import datetime

from urllib.parse import urljoin

import pandas as pd


service = Service("/usr/bin/chromedriver")

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=service, options=options)

url = "https://books.toscrape.com/index.html" # url de la página principal
driver.get(url) # carga la página

main_page_soup = BeautifulSoup(driver.page_source, "html.parser") # parsea el HTMl

"""
Seleccionamos todos los ítems que contienen una etiqueta <a> en la lista lateral. Estos tienen 
las categorías. Se seleccionan los <a> porque conviene, ya que necesitamos guardar la url de 
cada categoría.
"""
category_items = main_page_soup.select("ul.nav-list ul li a")
data_category = [] # en esta lista se guardará lo que extraigamos inicialmente

for item in category_items: # recorre todos los <a>
    category_name = item.get_text(strip = True) # strip = True es para eliminar los espacios inic. y final
    category_url = urljoin(url, item.get("href")) # el "href" contiene el link. urljoin resuelve la url
    
    driver.get(category_url) #viajamos a la url de la categoría 

    category_soup = BeautifulSoup(driver.page_source, "html.parser") 

    # Este strong era el que mostraba los resultados obtenidos al dar click a cada categoría
    strong = category_soup.select_one("form.form-horizontal strong") 
    category_total_books = int(strong.get_text(strip=True))

    # Añadimos a la lista un diccionario con los datos, para después transformarlo en un dataframe
    data_category.append({
        "categoria":category_name,
        "url_categoria":category_url,
        "cantidad_libros":category_total_books,
        "fecha_extraccion":datetime.now(), # obtener la fecha actual para guardarla en extracción
        "extraido_por":"Miguel Zuleta"
    })

category_dataframe = pd.DataFrame(data_category) # primero pasar a dataframe

# Convertir de DF a parquet. index = False es para que no añada una columna de índice a cada registro
category_dataframe.to_parquet("categorias.parquet", index = False)

data_book = [] # en esta lista guardamos la info. asociada a los libros

# Calculamos primero los resultados encontrados para la primera página muestra el total de libros, que es 1000
total_results = int(main_page_soup.select_one("form.form-horizontal strong").get_text()) 
# Obtenemos el dato de cuántos muestra por página (ej: Showing 1 to **20**)
total_per_page = int(main_page_soup.select("form.form-horizontal strong")[2].get_text())
# Calculamos las páginas totales dividiendo el total de libros entre la cantidad mostrada por página
total_pages = int(total_results / total_per_page)

for page_number in range(1, total_pages + 1):
    # Cada url de página cambia únicamente en un número: page_number en este caso
    page_url = f"https://books.toscrape.com/catalogue/category/books_1/page-{page_number}.html"
    driver.get(page_url)
    page_soup = BeautifulSoup(driver.page_source, "html.parser")

    links_to_detail_pages = page_soup.select("article.product_pod h3 a") # Link a página de detalle
    
    for link in links_to_detail_pages:
        detail_url = urljoin(page_url, link.get("href"))
        driver.get(detail_url)
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

        upc = detail_soup.select_one("table.table-striped td").get_text()
        title = detail_soup.select_one("div.product_main h1").get_text()
        book_category = detail_soup.select("ul.breadcrumb li")[2].get_text(strip = True)
        description_element = detail_soup.select_one("#product_description + p") # acá el "+" significa que el <p> es hermano directo del elemento con ese id
        description = (
            description_element.get_text(strip=True)
            if description_element # comprueba si hay descripción
            else ""
        )
        product_type = detail_soup.select("table.table-striped td")[1].get_text()

        price_tax_free = float(
            detail_soup.select("table.table-striped td")[2]
            .get_text(strip=True)
            .replace("£", "") #elimina la moneda y guarda el valor numérico
        )

        price_with_tax = float(
            detail_soup.select("table.table-striped td")[3]
            .get_text(strip=True)
            .replace("£", "")
        )

        tax = float(
            detail_soup.select("table.table-striped td")[4]
            .get_text(strip=True)
            .replace("£", "")
        )

        # todos los precios están en la misma moneda, por lo que este valor queda fijo
        currency = "GBP"
        availability = detail_soup.select("table.table-striped td")[5].get_text()
        # busca los números en el texto de disponibilidad (si no hay, pone 0)
        stock = int("".join(n for n in availability if n.isdigit()) or 0)
        # Asocia una calificación en texto a un número entero
        ratings = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5
        }

        # Obtiene el texto que contiene la clase (ejemplo: "Five")
        rating = ratings[detail_soup.find("p", class_="star-rating")["class"][1]] 

        reviews = int(detail_soup.select("table.table-striped td")[6].get_text())
        img_element = detail_soup.select_one("div.item.active img")

        # Resuelve la url de la imagen obtieniendo el atributo src y usando el link de la página de detalle
        img_url = urljoin(detail_url, img_element.get("src")) 

        data_book.append({
            "upc": upc,
            "titulo": title,
            "categoria": book_category,
            "descripcion": description,
            "tipo_producto": product_type,
            "precio_sin_impuesto": price_tax_free,
            "precio_con_impuesto": price_with_tax,
            "impuesto": tax,
            "moneda": currency,
            "disponibilidad": availability,
            "cantidad_stock": stock,
            "calificacion": rating,
            "cantidad_resenas": reviews,
            "url_libro": detail_url,
            "url_imagen": img_url,
            "fecha_extraccion": datetime.now(),
            "extraido_por": "Miguel Zuleta"
        })

book_dataframe = pd.DataFrame(data_book)

book_dataframe.to_parquet("libros.parquet", index=False)

driver.quit() # cerrar el driver del navegador.
