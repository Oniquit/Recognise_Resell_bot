# Recognize_Parse_bot

<h1 align='center' height='32'> Как локально запустить Recognize&Parse бот </h1>
<h2 align='center'>Этот бот по фото может определить название любого LEGO и найти его на реселлинговых площадках и магазинах.</h2> 

1. Получить в @Botfather токен для своего бота.
2. Открыв код, через терминал своего редактора установить через терминал библиотеку python-dotenv:

```pip install python-dotenv```

3. Далее втерминале установить и активировать виртуальное окружение:

```python3 -m venv env```

Для MacOS:

```source env/bin/activate```

Для Windows:

```env\Scripts\activate```

4. Создать в папке файл .env и внести туда токен для бота в формате TOKEN=, без кавычек после равно вставить токен и запустить бота. Если работаете в репозитории, то добавьте .env в .gitignore
                       