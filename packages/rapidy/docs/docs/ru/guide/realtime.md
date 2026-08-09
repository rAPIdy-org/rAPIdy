# WebSocket, SSE и streaming

WebSocket объявляется через `@websocket`, а не через HTTP `@get`. Хендлер получает `WebSocket`, поддерживающий
accept/reject/close, text/bytes/JSON и async iteration. Header/Cookie/Path/Query извлекаются при handshake; `Body` для
WebSocket запрещён. Peer disconnect, включая transport failure во время `send`, превращается в
`WebSocketDisconnect` без application-error traceback. При прямом lifespan shutdown rAPIdy запрашивает code 1001 для
ещё открытых accepted connections; process server может закрыть их раньше собственным restart code, поэтому signal
behavior зависит от runtime.

HTTP middleware не оборачивают WebSocket handshake. Host/Origin policy задаётся через
`rapidy.security.WebSocketSecurityConfig`; это особенно важно для credentials из cookies.

`SSEResponse` принимает асинхронный поток строк, dict или `SSEEvent`, формирует `text/event-stream`, retry/id/event
поля и не выставляет `Content-Length`. CR, LF и CRLF внутри data нормализуются в отдельные строки `data:`, поэтому
недоверенное содержимое не может внедрить новое SSE-поле или событие. Event name и id отклоняют CR/LF, id также
отклоняет NUL, а `retry` должен быть неотрицательным целым числом.

`StreamResponse` отправляет bytes или text инкрементально. Доступен и императивный API `prepare` → `write` →
`write_eof`. При disconnect iterable закрывается, а REQUEST-финализаторы DI выполняются.

Исполняемый пример всех трёх режимов:
[`examples/realtime.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/realtime.py).
