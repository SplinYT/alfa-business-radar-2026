# API v0.1

JSON UTF-8, same-origin. Сервер :8000. Ошибки: `{ "error": "описание" }`.

| Метод и путь | Вход | Результат |
|---|---|---|
| GET /health | нет | `{status:"ok"}` |
| POST /api/login | `{password}` | HttpOnly cookie + `{csrf}` |
| GET /api/session | cookie | `{csrf,roles}` |
| GET /api/companies?q=&large=1 | cookie, строка поиска | До 100 профилей, доступных тестовой учётной записи |
| POST /api/analyze | cookie, X-CSRF-Token, `{company,role,as_of:"YYYY-MM-DD"}` | company, role, cards, trace, as_of |
| POST /api/news | cookie, X-CSRF-Token, `{title,text,date,url}` | Нормализованная новость с hash ID |
| GET /api/bank?id= | cookie | `{id,document,page,text}` |
| POST /api/logout | cookie, X-CSRF-Token, `{}` | Сброс cookie |

`cards[]`: news (source), score (0–100), reasons[], evidence[] (document/page/quote/id), insight (summary/risks/opportunities/actions/bank_position/mode, опционально claims/model), warning, trace[].

Поля `claims[].source_ids` ссылаются на evidence. `risks`, `opportunities`, `actions` — сценарии, а не доказанные события. Source URL не означает, что подлинность новости проверена. Synthetic=true явно отделяет демонстрационную новость. Интерфейс экранирует все входные тексты.

Модель данных: companies(id,revenue,payload), payments(payer,beneficiary,amount,count), links(person,company), bank(id,document,page,text), news(id,payload), audit(id,at,company,action,payload), llm_budget(day,reserved). Индексы на отправителя, получателя и связи. SQLite подходит для прототипа; для масштабирования — PostgreSQL + поисковый индекс, workers импорта, очередь задач, tenant ACL и cache. Эти внешние компоненты не реализованы и не нужны для запуска.
