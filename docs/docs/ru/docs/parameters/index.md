# Request parameters
## Что такое параметр
Параметром в **rAPIdy** - это объект представляющий метаинформацию для типа данных, которые он извлекает.

Для того чтобы сообщить **rAPIdy** о своих намерениях извлечь данные из определенного места, воспользуйтесь конструкцией
`Annotated[str, <rapidy_param>]`.

Прочитать про тип `Annotated` можно **<a href="https://docs.python.org/3/library/typing.html#typing.Annotated" target="_blank">здесь</a>**.

Опираясь на тот тип, что пользователь передаст в качестве второго аргумента в 
**<a href="https://docs.python.org/3/library/typing.html#typing.Annotated" target="_blank">typing.Annotated</a>**,
**rAPIdy** поймет что требуется сделать с данными, которые ожидает сервер. 

Параметр в **rAPIdy** умеет все то же, что умеет 
**<a href="https://docs.pydantic.dev/latest/concepts/fields/" target="_blank">pydantic.Field</a>**
<i>(и даже чуть больше)</i>, это значит что все виды валидации
которые поддерживает **pydantic**, поддерживает и **rAPIdy-параметр**.

!!! example ""
    ```Python hl_lines="11-20"
    {!> ./parameters/index/ex_01.py !}
    ```

!!! tip ""
    Вы можете использовать `pydantic.Field` и  `rAPIdy-параметр` если требуется описать [схему](#schema) данных.

## Виды параметров
### Param
Одиночный параметр, используется тогда, когда вам необходимо точечно извлекать поступающие данные.

!!! example ""
    ```Python hl_lines="10 11"
    {!> ./parameters/index/ex_02.py !}
    ```

??? tip "Все типы параметров"
    <ul> 
      <li>[Path](path.md#path)</li>
      <li>[Header](header.md#header)</li>
      <li>[Cookie](cookie.md#cookie)</li>
      <li>[Query](query.md#query)</li>
      <li>BodyJson</li>
      <li>FormDataBody</li>
      <li>MultipartBody</li>
    </ul>

### Schema
Параметр-схема удобен тогда, когда вам нужно извлекать большое количество данных.

!!! example ""
    ```Python hl_lines="9 10 15"
    {!> ./parameters/index/ex_03.py !}
    ```
??? tip "Все типы параметров-схем"
    <ul> 
      <li>[PathSchema](path.md#pathschema)</li>
      <li>[HeaderSchema](header.md#headerschema)</li>
      <li>[CookieSchema](cookie.md#cookieschema)</li>
      <li>[QuerySchema](query.md#queryschema)</li>
      <li>BodyJsonSchema</li>
      <li>FormDataBodySchema</li>
      <li>MultipartBodySchema</li>
    </ul>

### Raw
Используйте `Raw-параметры` когда вам не требуется валидация.

!!! example ""
    ```Python hl_lines="12"
    {!> ./parameters/index/ex_04.py !}
    ```

??? tip "Все типы raw-параметров"
    <ul> 
      <li>[PathRaw](path.md#pathraw)</li>
      <li>[HeaderRaw](header.md#headerraw)</li>
      <li>[CookieRaw](cookie.md#cookieraw)</li>
      <li>[QueryRaw](query.md#queryraw)</li>
      <li>BodyJsonRaw</li>
      <li>FormDataBodyRaw</li>
      <li>MultipartBodyRaw</li>
      <li>TextBody</li>
      <li>BytesBody</li>
      <li>StreamBody</li>
    </ul>

!!! tip ""
    Подробнее о значениях по умолчанию см в разделе [Default values](../default_values.md)

Все сценарии применения вы найдете в разделе каждого параметра и в примерах - **[Examples](../../examples.md)**.
