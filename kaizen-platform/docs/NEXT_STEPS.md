# Próximas etapas

## Etapa 2 — dados reais e sincronização — implementada

- criar entidades de focos, hábitos, metas e tarefas;
- implementar criar, editar, concluir, arquivar e excluir;
- importar com segurança os dados locais do protótipo;
- sincronizar alterações entre dispositivos sem duplicações;
- conectar as telas atuais à API e remover a simulação de login.

## Etapa 3 — autenticação externa e entrega — base implementada

- verificação de e-mail;
- provedor transacional de e-mail por SMTP;
- provedor de SMS pela Twilio;
- OAuth/OIDC do Google com vínculo de conta, PKCE e troca de uso único;
- limitação distribuída de tentativas e registros de auditoria.

## Etapa 4 — PWA e aplicativo — base implementada

- interface, configuração, ícones e service worker versionáveis;
- modo offline e fila de sincronização com repetição idempotente e conflitos visíveis;
- configuração Capacitor pronta; ainda faltam gerar e assinar os projetos das lojas;
- armazenar credenciais nativas no Keychain/Keystore;
- finalizar os deep links OAuth nos projetos Android/iOS gerados;
- testar acessibilidade e responsividade em Android, iOS e tablets.

## Etapa 5 — homologação gratuita — configuração preparada

- banco PostgreSQL Neon e URL compatível com asyncpg;
- Blueprint Render Free com migrações, variáveis protegidas e health check;
- Cloudflare Pages com proxy de mesma origem para `/api`;
- recuperação por e-mail via API HTTPS da Brevo;
- disparo dos lembretes por rota interna e cron-job.org;
- falta criar as contas, cadastrar as credenciais e executar o primeiro deploy.

## Etapa 6 — publicação definitiva

- migrar o backend para uma instância sem partida fria e com disponibilidade contratada;
- configurar domínio próprio, backups testados, observabilidade, auditoria e rate limiting;
- gerar os pacotes assinados e preparar Play Store e App Store.
