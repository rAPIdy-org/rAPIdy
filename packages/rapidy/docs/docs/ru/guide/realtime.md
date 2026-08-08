# WebSocket, SSE и streaming

WebSocket объявляется через `@websocket`, а не через HTTP `@get`. Хендлер получает `WebSocket`, поддерживающий
accept/reject/close, text/bytes/JSON и async iteration. Header/Cookie/Path/Query извлекаются при handshake; `Body` для
WebSocket запрещён. На shutdown принятые соединения получают close code 1001.

`SSEResponse` принимает асинхронный поток строк, dict или `SSEEvent`, формирует `text/event-stream`, retry/id/event
поля и не выставляет `Content-Length`.

`StreamResponse` отправляет bytes или text инкрементально. Доступен и императивный API `prepare` → `write` →
`write_eof`. При disconnect iterable закрывается, а REQUEST-финализаторы DI выполняются.

Исполняемый пример всех трёх режимов:
[`examples/realtime.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/realtime.py).
