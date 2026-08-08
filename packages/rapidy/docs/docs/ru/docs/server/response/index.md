# HTTP-ответ
Раздел описывает как можно сформировать и отправить HTTP-ответ в **`Rapidy`**.

## Описание
**HTTP-ответ** — это сообщение, которое сервер отправляет клиенту в ответ на его запрос.

??? example "Пример текстового HTTP-ответа (протокол HTTP/1.1)"
    ```
    {!> ./docs/docs/server/response/01_text_response_example.txt !}
    ```

### Структура HTTP-ответа
HTTP-ответ состоит из стартовой строки, заголовков и тела.

#### Стартовая строка
`HTTP/1.1 200 OK`

Стартовая строка (или строка статуса) включает:

- **Версию протокола** *(HTTP-протокол)* — <span class="note-color">HTTP/1.1</span>
- **Код состояния** *(числовой код, обозначающий статус запроса)* — <span class="green-color">200</span>
- **Пояснение** *(краткое текстовое описание кода состояния)* — OK

??? info "Версии HTTP-протокола"
    HTTP-стандарты разрабатываются Internet Engineering Task Force (IETF) и World Wide Web Consortium (W3C), что приводит к публикации серии документов
    Requests for Comments (RFC).

    | Версия протокола | Тип HTTP-протокола | Транспортный уровень | Описание                                                                                 |
    | ---------------- | ------------------ | -------------------- | ---------------------------------------------------------------------------------------- |
    | HTTP/1.1         | Текстовый          | TCP                  | Требует дожидаться ответа перед отправкой следующего запроса в рамках одного соединения. |
    | HTTP/2           | Бинарный           | TCP                  | Позволяет отправлять несколько запросов одновременно без ожидания завершения предыдущих. |
    | HTTP/3/QUIC      | Бинарный           | UDP                  | Работает поверх UDP (использует технологию QUIC).                                        |

??? info "Коды состояния HTTP"
    HTTP-коды состояния сообщают клиенту результат обработки его запроса. Они делятся на пять категорий:

    | Код     | Описание                                                                           |
    | ------- | ---------------------------------------------------------------------------------- |
    | **1xx** | Информационные коды, не влияющие на обработку запроса.                             |
    | **2xx** | Успешная обработка запроса.                                                        |
    | **3xx** | Перенаправление клиента на другой ресурс.                                          |
    | **4xx** | Ошибки на стороне клиента (например, неверный запрос или недостаток прав доступа). |
    | **5xx** | Ошибки на стороне сервера.                                                         |

#### Заголовки ответа
Заголовки ответа (Response Headers) уточняют детали ответа, и никак не влияют на содержимое тела.

??? example "Примеры заголовков"
    | Категория  | Пример                          | Описание                                                    |
    |------------|---------------------------------|------------------------------------------------------------ |
    | Server     | Server: nginx                   | Информация о сервере, обработавшем запрос.                  |
    | Set-Cookie | Set-Cookie:UserData=SomeData123 | Cookie с информацией о пользователе, сохраняемой браузером. |

#### Тело ответа
Опциональная часть ответа, содержащая данные.

Сервер указывает тип передаваемых данных с помощью заголовка `Content-Type`.

Тело ответа может представлять собой JSON, медиафайл, документ, текст или даже произвольный набор байтов.

## Формирование HTTP-ответа
Простой ответ http-обработчика может выглядеть так:
```python
{!> ./docs/docs/server/response/02_simple_response_example.py !}
```

### Валидация и сериализация ответа
Для валидации и сериализации ответов `Rapidy` использует `pydantic`.

!!! info "При запуске сервера `Rapidy` создает `pydantic`-модель для каждого обработчика на основе аннотации возврата и использует её для валидации данных в ответе."

!!! tip "Можно переопределить тип для валидации или отменить создание `pydantic`-модели с помощью атрибутов `response_validate` и `response_type`."
    ```python hl_lines="5"
    {!> ./docs/docs/server/response/handler_response/response_validate.py !}
    ```

    !!! info "Подробнее об аттрибутах ответа для http-обработчика можно прочитать [здесь](handler_response)."


??? example "Примеры успешных ответов"
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/01_success/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/01_success/02_example.py !}
    ```
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/01_success/03_example.py !}
    ```

??? example "Примеры неуспешных ответов"
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/01_example/example.py !}
    ```
    ```text
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/01_example/response.txt !}
    ```

    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/02_example/example.py !}
    ```
    ```text
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/02_example/response.txt !}
    ```

### Продвинутый уровень управления HTTP-ответом
Для управления HTTP-ответами `Rapidy` использует объект `Response`.
```python
{!> ./docs/docs/server/response/03_response_import.py !}
```

Объект `Response` может быть создан как самим `Rapidy` внутри себя для формирования ответа, так и разработчиком для явного управления им.

!!! info "Подробнее об объекте `Response` можно прочитать [здесь](response_object)."

#### Автоматическое создание Response-объекта
`Rapidy` автоматически создает `Response` в следующих случаях:

**В обработчике определен атрибут с любым именем и типом `Response`**
```python
{!> ./docs/docs/server/response/04_response_inject.py !}
```

Это даёт разработчику больше гибкости в управлении `HTTP`-ответами, позволяя, например, устанавливать статус-код, cookies и другие параметры.
Подробнее о параметрах объекта `Response` можно узнать [здесь](response_object/#_1).

```python hl_lines="5 9 12"
{!> ./docs/docs/server/response/05_response_inject_ext.py !}
```

Также можно вернуть этот же `Response` объект.
```python hl_lines="5"
{!> ./docs/docs/server/response/06_return_injected_response.py !}
```

**Обработчик возвращает `python` объект**
```python hl_lines="5"
{!> ./docs/docs/server/response/02_simple_response_example.py !}
```

!!! info "Если в обработчике уже определён атрибут с типом `Response`, а сам обработчик возвращает `python`-объект, то новый экземпляр `Response` создаваться не будет."
    ```python hl_lines="5"
    {!> ./docs/docs/server/response/07_injected_response_not_recreated.py !}
    ```

#### Обработчик возвращает Response-объект
`Rapidy` позволяет разработчику самостоятельно управлять и формировать `Response` объект.

```python
{!> ./docs/docs/server/response/13_new_response_obj.py !}
```

!!! warning "При прямом управлении ответом атрибуты веб-обработчика игнорируются"

    ```python
    {!> ./docs/docs/server/response/08_ignore_content_type.py !}
    ```

!!! warning "Если `Response` объект был проброшел в аттрибут, а разработчик отдает новый `Response` то проброшенный `Response` игнорируется."

    ```python hl_lines="9"
    {!> ./docs/docs/server/response/09_ignore_injected_response.py !}
    ```

!!! note "При прямом управлении ответом валидация `pydantic` не будет работать."

    ```python hl_lines="5"
    {!> ./docs/docs/server/response/10_response_obj_pydantic.py !}
    ```

#### Обработчик возвращает None
Если обработчик `Rapidy` ничего не возвращает, то по умолчанию `Rapidy` вернет текущий `Response` объект.

!!! warning "Если вы изменили запрос и ничего не вернули из обработчика, то будет отдан именно этот измененный запрос!"

```python
{!> ./docs/docs/server/response/12_none_return.py !}
```

#### Атрибуты http-обработчиков
Атрибуты ответа веб-обработчика используются для управления формированием ответа при возврате любого `python`-объекта из обработчика.

##### Код состояния по умолчанию
Для управления кодом состояния по умолчанию вы можете определить атрибут `status_code`.

```python hl_lines="6 13"
{!> ./docs/docs/server/response/handler_response/status_code.py !}
```

!!! info "Об остальных аттрибутах можно прочитать [здесь](handler_response)."

!!! tip "Rapidy позволяет управлять атрибутами во всех типах обработчиков, включая те, что оформлены в стиле aiohttp."
    ```python hl_lines="12 13"
    {!> ./docs/docs/server/response/handler_response/aiohttp_style_example.py !}
    ```
