# Backend do Kaizen Life

API Python compartilhada pelo site, pela PWA e pelos futuros aplicativos Android e iOS.

## O que já está implementado

- cadastro e login com e-mail e senha forte;
- verificação do e-mail por código;
- acesso e criação de conta por código de telefone;
- acesso oficial do Google por OAuth/OIDC com `state`, `nonce`, PKCE e código de troca de uso único;
- vínculo seguro do Google a uma conta de mesmo e-mail já verificado;
- recuperação genérica por e-mail ou telefone, sem revelar se a conta existe;
- entrega de e-mail por SMTP ou API HTTPS da Brevo e de SMS pela Twilio, selecionável por ambiente;
- senha protegida com Argon2;
- access token JWT curto (15 minutos por padrão);
- refresh token aleatório, armazenado como hash, rotacionado e enviado em cookie HttpOnly;
- encerramento e revogação de sessões;
- limite de cinco tentativas e validade configurável para códigos;
- SQLite para desenvolvimento e PostgreSQL para produção;
- migrações Alembic, Dockerfile, Docker Compose e testes básicos.
- CRUD persistente de focos, hábitos, metas e tarefas;
- histórico diário dos hábitos, exclusão lógica e controle de versão para sincronização;
- Web Push para o site/PWA e FCM para Android/iOS;
- worker de lembretes de hábitos, tarefas e metas, com deduplicação e horário silencioso.
- rota protegida para acionar lembretes por um agendador HTTP gratuito.

## Executar localmente

Requer Python 3.12 ou superior.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

No Windows PowerShell, ative o ambiente com:

```powershell
.venv\Scripts\Activate.ps1
```

Abra:

- documentação interativa: `http://127.0.0.1:8000/docs`;
- status da API: `http://127.0.0.1:8000/api/v1/health`;
- prontidão do banco: `http://127.0.0.1:8000/api/v1/ready`.

No modo local, os códigos também aparecem no terminal e no campo `debug_code` da resposta.
Esse campo desaparece quando `KAIZEN_DEBUG=false`.

## Executar com PostgreSQL e Docker

```bash
cp .env.example .env
docker compose up --build
```

O Compose inicia site, PostgreSQL, API e worker de notificações. Abra
`http://localhost:8080`. Ele é uma conveniência de desenvolvimento; troque todas as
credenciais e segredos antes de publicar.

## Migrações

No desenvolvimento, `KAIZEN_AUTO_CREATE_TABLES=true` cria as tabelas automaticamente. Em
homologação e produção, use migrações:

```bash
alembic upgrade head
```

Depois configure `KAIZEN_AUTO_CREATE_TABLES=false`.

## Rotas disponíveis

| Método | Rota | Uso |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Cadastrar com e-mail e senha |
| `POST` | `/api/v1/auth/login` | Entrar com e-mail e senha |
| `POST` | `/api/v1/auth/email/verification/request` | Pedir verificação do e-mail |
| `POST` | `/api/v1/auth/email/verification/confirm` | Confirmar verificação do e-mail |
| `POST` | `/api/v1/auth/phone/request` | Pedir código por telefone |
| `POST` | `/api/v1/auth/phone/verify` | Validar código e entrar |
| `GET` | `/api/v1/auth/google/start` | Iniciar OAuth do Google |
| `GET` | `/api/v1/auth/google/callback` | Callback registrado no Google |
| `POST` | `/api/v1/auth/google/exchange` | Trocar o código temporário pela sessão |
| `POST` | `/api/v1/auth/recovery/request` | Pedir recuperação genérica |
| `POST` | `/api/v1/auth/recovery/confirm` | Confirmar código e recuperar |
| `POST` | `/api/v1/auth/refresh` | Rotacionar sessão pelo cookie |
| `POST` | `/api/v1/auth/logout` | Revogar e apagar o cookie |
| `GET` | `/api/v1/auth/me` | Obter a conta autenticada |
| `GET/POST/PATCH/DELETE` | `/api/v1/focuses` | Gerenciar focos |
| `GET/POST/PATCH/DELETE` | `/api/v1/habits` | Gerenciar hábitos |
| `PUT/DELETE` | `/api/v1/habits/{id}/completions/{data}` | Marcar hábito no dia |
| `GET/POST/PATCH/DELETE` | `/api/v1/goals` | Gerenciar metas |
| `GET/POST/PATCH/DELETE` | `/api/v1/tasks` | Gerenciar tarefas |
| `GET` | `/api/v1/sync/pull` | Buscar alterações e exclusões |
| `GET` | `/api/v1/notifications/status` | Consultar dispositivos e preferências |
| `PUT` | `/api/v1/notifications/preferences` | Salvar tipos e horário silencioso |
| `POST` | `/api/v1/notifications/devices` | Registrar Web Push ou FCM |
| `POST` | `/api/v1/notifications/devices/remove` | Remover o dispositivo da conta |
| `POST` | `/api/v1/notifications/test` | Enviar uma notificação de teste |
| `GET` | `/api/v1/health` | Verificar o processo |
| `GET` | `/api/v1/ready` | Verificar processo e banco |

Nas chamadas do navegador, use `credentials: "include"` para permitir o cookie de sessão. Guarde
o access token somente em memória e envie `Authorization: Bearer <token>` nas rotas protegidas.

## Configuração obrigatória antes da produção

1. Gere um segredo com `python -c "import secrets; print(secrets.token_urlsafe(64))"` e use-o em
   `KAIZEN_JWT_SECRET`.
2. Configure `KAIZEN_ENVIRONMENT=production`, `KAIZEN_DEBUG=false`,
   `KAIZEN_COOKIE_SECURE=true`, `KAIZEN_AUTO_CREATE_TABLES=false` e os domínios exatos no CORS.
3. Use PostgreSQL gerenciado e execute `alembic upgrade head` no processo de release.
4. Configure os provedores de e-mail/SMS e o Google OAuth descritos abaixo.
5. Adicione limitação distribuída de requisições para login e códigos antes de abrir cadastros.
6. Mantenha site e API no mesmo domínio sempre que possível, por exemplo `kaizen.app` e
   `kaizen.app/api`, para simplificar a segurança dos cookies.

O validador de configuração impede iniciar em produção com segredo fraco, depuração ativa,
cookie inseguro ou entrega de códigos pelo terminal.

## Configurar e-mail e SMS reais

Para e-mail, selecione SMTP e informe o servidor do provedor transacional:

```env
KAIZEN_EMAIL_DELIVERY_MODE=smtp
KAIZEN_SMTP_HOST=smtp.seu-provedor.com
KAIZEN_SMTP_PORT=587
KAIZEN_SMTP_USERNAME=USUARIO
KAIZEN_SMTP_PASSWORD=SEGREDO
KAIZEN_SMTP_FROM_EMAIL=contato@seu-dominio.com
KAIZEN_SMTP_FROM_NAME=Kaizen Life
KAIZEN_SMTP_SECURITY=starttls
```

Para SMS, selecione Twilio. O remetente precisa ser um número habilitado na conta:

```env
KAIZEN_SMS_DELIVERY_MODE=twilio
KAIZEN_TWILIO_ACCOUNT_SID=ACxxxxxxxx
KAIZEN_TWILIO_AUTH_TOKEN=SEGREDO
KAIZEN_TWILIO_FROM_PHONE=+15551234567
```

No desenvolvimento, `console` continua exibindo o código no terminal. Em produção, use um
provedor real ou `disabled`; o validador impede iniciar com `console`.

No Render Free, prefira a API HTTPS da Brevo porque as portas SMTP comuns são bloqueadas:

```env
KAIZEN_EMAIL_DELIVERY_MODE=brevo
KAIZEN_BREVO_API_KEY=SEGREDO
KAIZEN_EMAIL_FROM_EMAIL=remetente-verificado@example.com
KAIZEN_EMAIL_FROM_NAME=Kaizen Life
```

## Configurar Google OAuth

1. No Google Cloud Console, crie um cliente OAuth do tipo **Aplicativo da Web**.
2. Cadastre exatamente o valor de `KAIZEN_GOOGLE_REDIRECT_URI` em **URIs de redirecionamento
   autorizados**. Para produção, use HTTPS.
3. Separe por vírgulas as origens que podem receber o retorno em
   `KAIZEN_OAUTH_RETURN_ORIGINS`. Não use curingas.
4. Configure:

```env
KAIZEN_GOOGLE_OAUTH_ENABLED=true
KAIZEN_GOOGLE_CLIENT_ID=CLIENT_ID.apps.googleusercontent.com
KAIZEN_GOOGLE_CLIENT_SECRET=SEGREDO
KAIZEN_GOOGLE_REDIRECT_URI=https://seu-dominio.com/api/v1/auth/google/callback
KAIZEN_OAUTH_RETURN_ORIGINS=https://seu-dominio.com,com.kaizenlife.app://oauth
```

O callback nunca coloca JWT ou refresh token na URL. Ele devolve um código aleatório, armazenado
como hash, válido por dois minutos e consumido uma única vez pelo frontend.

## Configurar notificações

O navegador só mostra a solicitação depois que a pessoa toca em **Permitir notificações**. Sem
consentimento, nenhum dispositivo é registrado.

Para Web Push, gere um par VAPID com o utilitário `vapid` fornecido pelo pacote `py-vapid`. Guarde a
chave privada em `backend/secrets/vapid_private.pem` e configure:

```env
KAIZEN_WEB_PUSH_ENABLED=true
KAIZEN_VAPID_PUBLIC_KEY=CHAVE_PUBLICA_BASE64URL
KAIZEN_VAPID_PRIVATE_KEY=/run/secrets/vapid_private.pem
KAIZEN_VAPID_SUBJECT=mailto:contato@seu-dominio.com
```

Para Android/iOS, coloque a conta de serviço do Firebase em
`backend/secrets/firebase-service-account.json` e configure:

```env
KAIZEN_FIREBASE_CREDENTIALS_PATH=/run/secrets/firebase-service-account.json
```

Em uma hospedagem sem arquivo secreto persistente, use o JSON completo em
`KAIZEN_FIREBASE_CREDENTIALS_JSON`.

O worker consulta lembretes a cada 30 segundos. Ele envia hábitos no horário escolhido, tarefas 30
minutos antes do prazo e metas às 09:00 do dia final. Cada evento possui uma chave de deduplicação.
Falhas repetidas desativam somente o dispositivo inválido.

O guia completo do ambiente gratuito está em [`../docs/FREE_DEPLOYMENT.md`](../docs/FREE_DEPLOYMENT.md).

## Testes

```bash
python -m unittest discover -s tests -v
pytest
```

Os testes unitários cobrem identificadores, senha, sequências e janelas de lembrete. Com as
dependências instaladas, o Pytest também executa cadastro, CRUD, criação idempotente da fila
offline, exclusão sincronizada, status de notificações e o estado desabilitado do Google OAuth.
