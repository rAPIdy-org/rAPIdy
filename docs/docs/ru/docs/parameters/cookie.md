# Cookie parameters
## Типы данных
### Cookie
!!! example "Cookie"
    ```Python hl_lines="10 11"
    {!> ./parameters/cookie/types/Cookie/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET --cookie "UserId=user_1;UserSession=awesome_session" http://127.0.0.1:8080
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1", "user_session": "awesome_session"}
        ```

### CookieSchema
!!! example "CookieSchema"
    ```Python hl_lines="9 10 15"
    {!> ./parameters/cookie/types/CookieSchema/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET --cookie "UserId=user_1;UserSession=awesome_session" http://127.0.0.1:8080
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1", "user_session": "awesome_session"}
        ```

### CookieRaw
!!! example "CookieRaw"
    ```Python hl_lines="11"
    {!> ./parameters/cookie/types/CookieRaw/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET --cookie "UserId=user_1;UserSession=awesome_session" http://127.0.0.1:8080
        ```
        вы получите ответ:
        ```
        {"cookies": {"UserId": "user_1", "UserSession": "awesome_session"}}
        ```

!!! warning "Внимание"
    CookieRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров.</a>
