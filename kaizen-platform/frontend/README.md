# Site e PWA

O arquivo `Kaizen-Life-Foco.html` agora usa a API quando é servido por HTTP/HTTPS. Se for aberto
diretamente como arquivo, mantém o modo de prévia local para facilitar o design sem servidor.

`kaizen-config.js` define a base da API. No Nginx/Docker ela permanece `/api/v1`, pois site e API
usam o mesmo domínio. Em outro provedor, informe a URL HTTPS completa.

O navegador registra `sw.js` e só solicita notificações depois do clique em **Permitir
notificações**. Web Push exige HTTPS, com exceção de `localhost`, aceito pelos navegadores para
desenvolvimento.

O service worker deixa a interface principal disponível offline. Criações e alterações de focos,
hábitos, metas, tarefas e conclusões de hábitos entram em uma fila IndexedDB quando a rede cai. A
fila repete os envios em ordem, combina edições consecutivas e usa IDs gerados no dispositivo para
não duplicar criações quando a resposta do servidor se perde.

Em **Configurações > Sincronização**, a pessoa vê quantas alterações aguardam envio, pode tentar
novamente e recebe um aviso quando outro dispositivo alterou a mesma versão. A ação **Usar dados do
servidor** exige confirmação e descarta somente as mutações bloqueadas, não toda a conta.

O botão Google abre o consentimento oficial quando `KAIZEN_GOOGLE_OAUTH_ENABLED=true`. No navegador,
o retorno usa a URL atual; no app Capacitor, usa o deep link `com.kaizenlife.app://oauth`.
