# JSON
Чтение тела запроса как `JSON`.

## Описание
**JSON** (JavaScript Object Notation) *(MIME-type: `application/json`)* — текстовый формат обмена структурированными данными, основанный на JavaScript. Сегодня JSON является языконезависимым и используется в различных языках программирования.

Этот раздел покажет, как извлекать `JSON` из тела запроса и валидировать его с помощью **`Rapidy`**.

## Типы данных в JSON

### Объект
Неупорядоченное множество пар «ключ:значение».
```json
{
    "username": "User",
    "password": "myAwesomePass"
}
```
```python
{!> ./docs/docs/server/request/parameters/body/json/01_obj/example.py !}
```
??? example "Отправка с помощью `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/01_obj/curl.sh !}
    ```

### Массив
```json
[
    {"username": "User1", "password": "myAwesomePass1"},
    {"username": "User2", "password": "myAwesomePass2"}
]
```
```python
{!> ./docs/docs/server/request/parameters/body/json/02_array/example.py !}
```
??? example "Отправка с помощью `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/02_array/curl.sh !}
    ```

### Число
Целое или вещественное значение.
```json
111
```
```python
{!> ./docs/docs/server/request/parameters/body/json/03_num/example.py !}
```
??? example "Отправка с помощью `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/03_num/curl.sh !}
    ```
!!! note "При отправке строки в формате JSON требуется дополнительное экранирование символов: `"111"`"

### Литералы
`true` (логическое «истина»), `false` (логическое «ложь») и `null` (отсутствие значения).
```json
true
false
null
```
```python
{!> ./docs/docs/server/request/parameters/body/json/04_literal/example.py !}
```
??? example "Отправка с помощью `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/04_literal/curl_true.sh !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/04_literal/curl_false.sh !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/04_literal/curl_null.sh !}
    ```

### Строка
```json
"SomeString"
```
```python
{!> ./docs/docs/server/request/parameters/body/json/05_str/example.py !}
```
??? example "Отправка с помощью `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/05_str/curl.sh !}
    ```
!!! note "При отправке строки в формате JSON требуется экранирование символов: `\"SomeString\"`"

---

## Кастомный JSON-декодер
По умолчанию `Rapidy` использует `json.loads` без параметров для декодирования входящего JSON.

!!! example "Эквивалентные примеры:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/01_default_decoder.py !}
    ```
    или
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/02_default_decoder.py !}
    ```

Для использования кастомного декодера передайте вызываемый объект, принимающий `str`, в параметр `json_decoder`.

!!! note "Ожидаемый тип: `Callable[[str], Any]`"

!!! example "Пример с пользовательским декодером:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/03_custom_decoder.py !}
    ```

Если необходимо использовать `json.loads` с параметрами, воспользуйтесь `functools.partial`:
```python
{!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/04_decoder_with_params.py !}
```

---

## Извлечение без валидации

!!! warning "Отключение валидации не рекомендуется."
    Если валидация отключена, параметр будет содержать данные в том виде, в котором их распаковал JSON-декодер.

### Способы отключения валидации

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/body/json/07_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/body/json/07_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
```python
{!> ./docs/docs/server/request/parameters/body/json/07_ignore_validation/03_no_type.py !}
```

---

## Значения по умолчанию
Если HTTP-запрос не содержит тела, параметр получит указанное значение по умолчанию (если оно задано).

### Примеры использования

#### Указано значение по умолчанию
```python
{!> ./docs/docs/server/request/parameters/body/json/08_default/01_default_exists.py !}
```

#### Опциональное тело запроса
```python
{!> ./docs/docs/server/request/parameters/body/json/08_default/02_default_optional.py !}
```

---

## Извлечение сырых данных
`Rapidy` использует метод `json` объекта `Request` для получения данных и передает их в `Pydantic` для валидации.

Если данные не удастся извлечь как JSON, будет возвращена ошибка `ExtractError`:
```json
{
    "errors": [
        {
            "type": "ExtractError",
            "loc": [
                "body"
            ],
            "msg": "Failed to extract body data as Json: <error_description>"
        }
    ]
}
```

??? info "Как происходит извлечение внутри `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/01_extract_raw.py !}
    ```

!!! note "`Rapidy` использует встроенные механизмы `aiohttp`"
    Подробнее об объекте `aiohttp.Request` и методах извлечения данных можно узнать
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

Однако если параметр аннотирован как `bytes` или `StreamReader`, данные извлекаются иначе.

!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

### `bytes`
```python
{!> ./docs/docs/server/request/parameters/body/json/09_extract_data/02_extract_bytes/01_handler_example.py !}
```
??? info "Внутренний код `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/02_extract_bytes/02_rapidy_code.py !}
    ```

### `StreamReader`
```python
{!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/01_handler_example.py !}
```
??? info "Внутренний код `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/02_rapidy_code.py !}
    ```

!!! warning "Валидация `Pydantic` для `StreamReader` не поддерживается."

??? warning "Невозможно задать значение по умолчанию для `StreamReader`."
    При попытке установить значение по умолчанию для `Body` с аннотацией `StreamReader` через `default` или
    `default_factory` будет поднята ошибка `ParameterCannotUseDefaultError`.
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/03_stream_reader_cant_default_text.txt !}
    ```
