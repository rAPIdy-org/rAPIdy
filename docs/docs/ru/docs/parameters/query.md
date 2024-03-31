# Query parameters
## Типы данных
### Query
!!! example "Query"
    ```Python hl_lines="10 11"
    {!> ./parameters/query/types/Query/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET 'http://127.0.0.1:8080?userId=user_1&userFilterValue=awesome_filter'
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1", "user_filter_value": "awesome_filter"}
        ```

### QuerySchema
!!! example "QuerySchema"
    ```Python hl_lines="9 10 15"
    {!> ./parameters/query/types/QuerySchema/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET 'http://127.0.0.1:8080?userId=user_1&userFilterValue=awesome_filter'
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1", "user_filter_value": "awesome_filter"}
        ```

### QueryRaw
!!! example "QueryRaw"
    ```Python hl_lines="11"
    {!> ./parameters/query/types/QueryRaw/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        Отправьте запрос с помощью `curl`:
        ```
        curl -X GET 'http://127.0.0.1:8080?userId=user_1&userFilterValue=awesome_filter'
        ```
        вы получите ответ:
        ```
        {"query_parameters_raw": {"userId": "user_1", "userFilterValue": "awesome_filter"}}
        ```

!!! warning "Внимание"
    QueryRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров

## Ключевые особенности

### Использование именованных ресурсов
 стоит ли указать, что я про это уже рассказывал?