---
hide:
  - navigation
---

<!-- RAPIDY_LEGACY_1X -->

> **⚠️ Legacy rAPIdy 1.x documentation.** This page is retained only for historical reference and may describe aiohttp APIs that do not exist in rAPIdy 2.0. Use the [current 2.0 documentation](https://rapidy.dev/) for new code.


# Why Rapidy?

**Rapidy is not just another framework.** It is a lightweight, fast, and powerful tool for building server applications, combining
**flexibility**, **performance**, and **ease of use**.

⚡ **Asynchronous, fast, and convenient** — everything you need for modern API development.

## Why is Rapidy better than others?

| **Framework** | **Asynchronous** | **Performance**       | **Simplicity** | **Auto API documentation** | **Validation & serialization in middleware** | **Unified body parsing interface** | **Flexible routing**            | **Client & Server** | **Native Python types** | **Lifecycle control** | **Fast validation & serialization** |
|---------------|------------------|-----------------------|----------------|----------------------------|----------------------------------------------|------------------------------------|---------------------------------|---------------------|-------------------------|-----------------------|-------------------------------------|
| **rAPIdy**    | ✅                | High (Aiohttp)        | ✅ Simple       | ❌ (coming soon)            | ✅                                            | ✅                                  | ✅                               | ✅ (aiohttp client)  | ✅                       | ✅                     | ✅ High                              |
| **FastAPI**   | ✅                | Very high (Starlette) | ✅ Simple       | ✅                          | ❌                                            | ❌                                  | 🟡 (class-based handler limits) | ❌ (server only)     | ✅                       | ✅                     | ✅ High                              |
| **Litestar**  | ✅                | Very high             | ✅ Simple       | ✅                          | ❌                                            | ✅                                  | ✅                               | ❌ (server only)     | ✅                       | ✅                     | 🚀 Very high (msgspec)              |
| **Aiohttp**   | ✅                | High                  | 🟡 Medium      | ❌                          | ❌                                            | ❌                                  | 🟡 (class-based handler limits) | ✅                   | ❌                       | 🟡                    | ❌ No                                |
| **Flask**     | 🟡 (ver >= 2.0)  | Moderate              | ✅ Simple       | 🟡 (via extensions)        | ❌                                            | ❌                                  | 🟡 (limited routing)            | ❌ (server only)     | ❌                       | ❌                     | ❌ No                                |
| **Django**    | 🟡 (ver >= 3.1)  | Low                   | ✅ Simple       | 🟡 (via extensions)        | ❌                                            | ❌                                  | ✅                               | ❌ (server only)     | ❌                       | ❌                     | 🐌 Low (slow serializers)           |

## Reasons to Choose Rapidy

✅ **Powerful Asynchronous Support with Aiohttp**
— Use **async/await** at all levels of request handling.

✅ **Flexibility & Versatility**
— Supports both client and server (FastAPI and Litestar do not).
— More flexible routing than FastAPI and Aiohttp.

✅ **Clean & User-Friendly API**
— Parses `body` uniformly for all request types.
— Fully compatible with Python types (similar to FastAPI and Litestar).

✅ **High Performance**
— Runs faster than Flask and Django.
— Validation and serialization **on par with FastAPI**.

✅ **Simplicity Without Losing Power**
— Easy to write and maintain code.

✅ **Framework Architecture**
— Rapidy’s source code is fully documented, ensuring transparency and ease of maintenance.
— The framework’s codebase follows a modular structure, allowing for high scalability and easier integration of new features.

---

## What's Next?

Rapidy is just getting started, and even more great features are coming:

🔹 **Automatic OpenAPI generation** (already in development!)
🔹 **HTTP client with full Pydantic support**
🔹 **Full-fledged GRPC**

⚡ **We are shaping the future of web development!** Subscribe for updates and be among the first to experience the new Rapidy features.

---

### Conclusion: **Rapidy — flexibility, speed, and convenience.**
Try it today and see for yourself! 🚀
