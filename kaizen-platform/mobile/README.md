# Aplicativo Android e iOS

Este projeto Capacitor reutiliza exatamente a interface da pasta `frontend`. O código da interface
já detecta o ambiente nativo, pede permissão após o clique do usuário, registra o token FCM no
backend e remove esse token no logout completo.

## Preparar

Antes do build de loja, troque o `apiBase` de `frontend/kaizen-config.js` pelo endereço HTTPS real
da API. O arquivo `kaizen-config.production.example.js` mostra o formato. O HTTP e os cookies do
Capacitor estão habilitados para que a renovação da sessão não dependa do comportamento da WebView.

```bash
cd mobile
npm install
npx cap add android
npx cap add ios
npm run sync
```

Use `npm run android` para abrir o Android Studio. Para iOS, `npm run ios` exige macOS e Xcode.

## Push nativo

1. Crie o projeto do aplicativo no Firebase.
2. Coloque `google-services.json` no projeto Android gerado.
3. No iOS, adicione `GoogleService-Info.plist`, habilite Push Notifications e vincule a chave APNs
   ao Firebase. O plugin FCM converte o token APNs recebido pelo Capacitor em um token FCM.
4. Guarde a conta de serviço somente no servidor. Use
   `KAIZEN_FIREBASE_CREDENTIALS_JSON` no Render ou aponte
   `KAIZEN_FIREBASE_CREDENTIALS_PATH` para um arquivo secreto em outra hospedagem.

Nunca coloque a conta de serviço do Firebase dentro do aplicativo. O app recebe apenas o token do
dispositivo; quem envia a notificação é o backend.

## Login Google no aplicativo

O pacote usa `@capacitor/browser` para abrir o Google fora da WebView e `@capacitor/app` para ouvir
o retorno `com.kaizenlife.app://oauth`. Depois de gerar os projetos nativos:

1. no Android, adicione um `intent-filter` para o scheme `com.kaizenlife.app` e host `oauth`;
2. no iOS, adicione `com.kaizenlife.app` em **URL Types**;
3. inclua `com.kaizenlife.app://oauth` em `KAIZEN_OAUTH_RETURN_ORIGINS` no backend;
4. mantenha como callback registrado no Google a URL HTTPS do backend, não o deep link.

Execute `npm run sync` após instalar ou alterar os plugins. A configuração nativa final só pode ser
validada depois que os projetos Android/iOS forem gerados em uma máquina com os respectivos SDKs.
