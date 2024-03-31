# Header parameters
## Типы данных
### Header
!!! example "Header"
    ```Python hl_lines="10 11"
    {!> ./parameters/header/types/Header/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET -H "Authorization: Token123" http://127.0.0.1:8080
        ```
        вы получите ответ:
        ```
        {"host": "127.0.0.1:8080", "auth_token": "Token123"}
        ```

### HeaderSchema
!!! example "HeaderSchema"
    ```Python hl_lines="9 10 15"
    {!> ./parameters/header/types/HeaderSchema/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET -H "Authorization: Token123" http://127.0.0.1:8080
        ```
        вы получите ответ:
        ```
        {"host": "127.0.0.1:8080", "auth_token": "Token123"}
        ```

### HeaderRaw
!!! example "HeaderRaw"
    ```Python hl_lines="11"
    {!> ./parameters/header/types/HeaderRaw/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET -H "Authorization: Token123" http://127.0.0.1:8080
        ```
        вы получите ответ:
        ```
        {"headers": "{"host": "127.0.0.1:8080", "auth_token": "Token123"}}
        ```

!!! warning "Внимание"
    HeaderRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров.</a>
