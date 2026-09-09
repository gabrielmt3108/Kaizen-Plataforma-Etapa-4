# Implantação gratuita do Kaizen Life

Esta configuração é adequada para começar, validar o produto e usar com poucos usuários. Ela não
é uma produção com disponibilidade garantida: o backend gratuito do Render adormece após um período
sem acessos e pode demorar aproximadamente um minuto para responder à primeira chamada.

## Arquitetura escolhida

| Parte | Serviço | O que fica nele | Custo inicial |
|---|---|---|---|
| Banco | Neon Free | usuários, sessões, focos, hábitos, metas, tarefas e dispositivos | gratuito dentro da franquia |
| Backend | Render Free | FastAPI, autenticação, sincronização e envio de notificações | gratuito dentro da franquia |
| Frontend | Cloudflare Pages | HTML, PWA, service worker e proxy `/api` | gratuito dentro da franquia |
| E-mail | Brevo Free | códigos de verificação e recuperação por API HTTPS | até 300 e-mails/dia no plano gratuito atual |
| Agendador | cron-job.org | chama a fila de lembretes a cada 10 minutos | gratuito |
| Push web | Web Push/VAPID | notificações autorizadas pelo navegador | gratuito |
| Push do app | Firebase Cloud Messaging | notificações Android/iOS autorizadas no aplicativo | sem custo para o FCM |

O SMS permanece desativado nesta fase. A Twilio oferece teste, mas o envio de SMS e a manutenção de
um número não são gratuitos de forma permanente.

## Onde cada credencial fica

| Credencial | Onde cadastrar | Pode ir ao frontend? |
|---|---|---|
| `KAIZEN_DATABASE_URL` | segredo do Render | não |
| `KAIZEN_JWT_SECRET` | gerado automaticamente pelo Render | não |
| `KAIZEN_CRON_SECRET` | segredo do Render e cabeçalho privado do cron-job.org | não |
| `KAIZEN_BREVO_API_KEY` | segredo do Render | não |
| `KAIZEN_GOOGLE_CLIENT_SECRET` | segredo do Render | não |
| `KAIZEN_VAPID_PRIVATE_KEY` | segredo do Render | não |
| `KAIZEN_VAPID_PUBLIC_KEY` | variável do Render, devolvida pela API ao navegador | sim, ela é pública |
| `KAIZEN_FIREBASE_CREDENTIALS_JSON` | segredo do Render | não |
| `KAIZEN_BACKEND_ORIGIN` | variável do Cloudflare Pages | sim, é apenas a URL pública da API |

Os arquivos `.env.example` contêm somente nomes e exemplos. Nenhuma credencial real deve ser
salva no Git, no HTML, em captura de tela ou enviada em conversa.

## 1. Colocar o projeto em um repositório

Crie um repositório privado no GitHub e coloque **o conteúdo desta pasta** na raiz do repositório,
de forma que `render.yaml`, `backend/`, `frontend/` e `functions/` fiquem no primeiro nível. Render
e Cloudflare farão novos deploys a cada atualização da branch principal.

## 2. Gerar os segredos próprios do Kaizen

Em um terminal, execute:

```bash
cd backend
python scripts/generate_secrets.py
```

O comando mostra duas linhas. Guarde-as em um gerenciador de senhas:

- `KAIZEN_JWT_SECRET`: assina os tokens de acesso. O `render.yaml` já pede ao Render para gerar
  outro valor seguro automaticamente, então o valor local serve para uma implantação manual;
- `KAIZEN_CRON_SECRET`: autentica apenas a chamada do agendador. O mesmo valor será colado no
  Render e no cabeçalho privado do cron-job.org.

Não reutilize senha de usuário, senha do Neon ou chave da Brevo nesses campos.

## 3. Criar o PostgreSQL no Neon

1. Crie um projeto no plano Free.
2. Para reduzir latência, escolha uma região próxima à região `Virginia` do backend, se estiver
   disponível.
3. No painel **Connect**, selecione a conexão com pooler e copie a connection string completa.
4. Guarde essa URL como `KAIZEN_DATABASE_URL` no Render.

A URL normalmente começa com `postgresql://` e pode terminar com
`sslmode=require&channel_binding=require`. O backend agora a converte automaticamente para o driver
assíncrono, mantém TLS obrigatório e remove o parâmetro incompatível. Não edite a senha manualmente.

## 4. Criar o remetente e a chave na Brevo

1. Crie uma conta gratuita na Brevo.
2. Em **Senders & IP**, cadastre e confirme o e-mail que aparecerá como remetente.
3. Em **SMTP & API > API Keys**, gere uma chave exclusiva chamada `Kaizen Render`.
4. Guarde a chave em `KAIZEN_BREVO_API_KEY` e o e-mail confirmado em
   `KAIZEN_EMAIL_FROM_EMAIL` no Render.

O backend usa a API HTTPS da Brevo, não SMTP. Isso é necessário porque o Render Free bloqueia as
portas SMTP comuns. Se a chave vazar, revogue-a na Brevo e gere outra.

## 5. Publicar primeiro o frontend no Cloudflare Pages

1. Abra **Workers & Pages > Create > Pages > Connect to Git** e selecione o repositório.
2. Use `None` como framework, `exit 0` como comando de build e `frontend` como diretório de saída.
3. Deixe o diretório raiz vazio, pois o repositório já começa na raiz da plataforma.
4. Faça o primeiro deploy e anote a origem recebida, por exemplo
   `https://kaizen-life.pages.dev` — sem a barra final.

Nesse primeiro deploy a interface abre, mas `/api` responde que o backend ainda não foi configurado.
Isso será resolvido depois da criação do Render.

## 6. Publicar a API no Render

1. Abra **New > Blueprint**, conecte o mesmo repositório e selecione o `render.yaml`.
2. Escolha o plano Free quando solicitado.
3. Preencha os campos secretos solicitados:

| Campo do Render | Valor |
|---|---|
| `KAIZEN_DATABASE_URL` | connection string copiada do Neon |
| `KAIZEN_CORS_ORIGINS` | origem exata do Cloudflare, como `https://kaizen-life.pages.dev` |
| `KAIZEN_OAUTH_RETURN_ORIGINS` | origem do Cloudflare e `com.kaizenlife.app://oauth`, separados por vírgula |
| `KAIZEN_BREVO_API_KEY` | chave criada na Brevo |
| `KAIZEN_EMAIL_FROM_EMAIL` | remetente verificado na Brevo |
| `KAIZEN_CRON_SECRET` | valor criado por `generate_secrets.py` |

O Blueprint instala o Python, executa `alembic upgrade head` no comando de inicialização, inicia o
FastAPI usando a porta do Render, habilita cookie HTTPS e cria `KAIZEN_JWT_SECRET` aleatório sem
gravá-lo no repositório. A migração está no início do comando porque o recurso separado de
*pre-deploy* do Render não está disponível no plano Free.
Quando terminar, anote a URL `https://kaizen-life-api....onrender.com`.

## 7. Ligar o Cloudflare ao Render

No projeto do Cloudflare Pages, abra **Settings > Environment variables** e crie:

```text
KAIZEN_BACKEND_ORIGIN=https://SUA-API.onrender.com
```

Use apenas a origem HTTPS, sem `/api/v1` e sem barra final. Cadastre em **Production** e, se quiser
testar branches, também em **Preview**. Faça um novo deploy.

A Function em `functions/api/[[path]].js` passa apenas as chamadas `/api/*` para o Render. Assim,
o site e a sessão HttpOnly continuam aparecendo ao navegador como uma única origem; a senha do
banco e os demais segredos nunca passam pelo Cloudflare ou pelo JavaScript da página.

## 8. Ativar o Google quando quiser

O deploy inicial deixa Google OAuth desligado para não exigir uma credencial antes da hora. Para
ativar:

1. No Google Cloud Console, configure a tela de consentimento e crie um cliente OAuth do tipo
   **Aplicativo da Web**.
2. Use a origem do Cloudflare em **Origens JavaScript autorizadas**.
3. Cadastre exatamente esta URI de redirecionamento:
   `https://SEU-PROJETO.pages.dev/api/v1/auth/google/callback`.
4. No Render, adicione `KAIZEN_GOOGLE_CLIENT_ID`, `KAIZEN_GOOGLE_CLIENT_SECRET` e
   `KAIZEN_GOOGLE_REDIRECT_URI` com os valores correspondentes.
5. Troque `KAIZEN_GOOGLE_OAUTH_ENABLED` para `true` e faça novo deploy.

O segredo do Google fica somente no Render. O callback retorna ao site um código temporário de uso
único, não um JWT na URL.

## 9. Ativar notificações do site

Instale as dependências do backend e gere um par VAPID:

```bash
cd backend
python -m pip install .
python scripts/generate_vapid_keys.py
```

Guarde a chave privada em um gerenciador de senhas. No Render, cadastre as duas linhas geradas,
adicione um `KAIZEN_VAPID_SUBJECT` como `mailto:seu-email@example.com`, altere
`KAIZEN_WEB_PUSH_ENABLED=true` e faça novo deploy.

O navegador continuará mostrando a permissão somente após uma ação explícita da pessoa. Se ela
negar, o Kaizen não registra nem envia notificações àquele dispositivo.

## 10. Agendar os lembretes

No cron-job.org, crie um job com:

- frequência: a cada 10 minutos;
- método: `POST`;
- URL: `https://SEU-PROJETO.pages.dev/api/v1/internal/notifications/dispatch`;
- cabeçalho: `X-Kaizen-Cron-Secret: O_MESMO_SEGREDO_DO_RENDER`.

A rota usa comparação segura do segredo, fica oculta quando o agendador está desativado e executa
os lembretes com deduplicação. A chamada periódica também reduz, mas não elimina, as partidas frias
do Render Free.

## 11. Preparar push nativo para Android e iOS

Quando o projeto móvel estiver no Firebase, copie o JSON da conta de serviço inteira para o segredo
`KAIZEN_FIREBASE_CREDENTIALS_JSON` no Render. O backend aceita esse JSON diretamente, sem depender
de um arquivo no disco efêmero. A configuração do aplicativo para receber o token FCM será feita na
etapa de empacotamento Android/iOS.

## 12. Verificação rápida

Depois dos deploys:

1. abra `https://SEU-PROJETO.pages.dev/api/v1/health` e confirme `{"status":"ok"}`;
2. abra `https://SEU-PROJETO.pages.dev/api/v1/ready` e confirme `{"status":"ready"}`;
3. crie uma conta, confirme o código recebido por e-mail e entre novamente;
4. autorize notificações, use o botão de teste e confira o dispositivo na conta;
5. execute manualmente o job do cron-job.org e confirme resposta `status: ok` no histórico;
6. confira no Neon se as tabelas e o novo usuário foram persistidos.

Se o primeiro acesso levar perto de um minuto, isso é a partida fria esperada do Render Free, não
uma perda de dados. O Neon continua guardando os dados fora do disco temporário do backend.
