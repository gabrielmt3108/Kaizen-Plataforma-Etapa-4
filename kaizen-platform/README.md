# Kaizen Life — plataforma

Quarta etapa da evolução do protótipo para uma plataforma com dados reais e implantação gratuita.

## Arquitetura escolhida

- **Site e PWA:** a interface atual continua sendo a única interface.
- **Aplicativo:** a mesma interface será empacotada com Capacitor para Android e iOS.
- **Backend:** FastAPI em Python, compartilhado pelo site e pelos aplicativos.
- **Banco:** SQLite apenas no desenvolvimento; PostgreSQL na hospedagem.

Essa abordagem evita recriar todas as telas em outra tecnologia. O Python fica no servidor,
onde autenticação, sincronização, regras e dados podem atender qualquer dispositivo.

## Conteúdo desta entrega

- [`backend/`](backend/): API executável, autenticação, recuperação e banco;
- [`frontend/`](frontend/): site instalável como PWA, com service worker e Web Push;
- [`mobile/`](mobile/): configuração Capacitor e ponte de notificações Android/iOS;
- [`deploy/`](deploy/): proxy Nginx para servir site e API no mesmo domínio;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): decisões para web, PWA e aplicativos;
- [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md): sequência segura das próximas entregas.
- [`docs/FREE_DEPLOYMENT.md`](docs/FREE_DEPLOYMENT.md): configuração gratuita do Neon, Render,
  Cloudflare Pages, Brevo e notificações agendadas.

Esta versão também inclui um Blueprint do Render, proxy de mesma origem no Cloudflare Pages,
PostgreSQL Neon, entrega de e-mail pela API da Brevo e uma rota autenticada para o agendador de
notificações. As integrações externas permanecem desligadas até que as credenciais do ambiente
sejam configuradas.

Comece pelo arquivo [`backend/README.md`](backend/README.md).
