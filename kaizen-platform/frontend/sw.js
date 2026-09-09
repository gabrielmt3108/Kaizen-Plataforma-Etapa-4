const CACHE_NAME = 'kaizen-life-v3';
const APP_SHELL = [
  './Kaizen-Life-Foco.html',
  './kaizen-config.js',
  './manifest.webmanifest',
  './kaizen-icon-192.png',
  './kaizen-icon-512.png'
];

self.addEventListener('install', function(event){
  event.waitUntil(caches.open(CACHE_NAME).then(function(cache){
    return cache.addAll(APP_SHELL);
  }).then(function(){ return self.skipWaiting(); }));
});

self.addEventListener('activate', function(event){
  event.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(key){ return key!==CACHE_NAME; }).map(function(key){
      return caches.delete(key);
    }));
  }).then(function(){ return self.clients.claim(); }));
});

self.addEventListener('fetch', function(event){
  const request = event.request;
  if(request.method!=='GET') return;
  const url = new URL(request.url);
  if(url.pathname.indexOf('/api/')===0) return;
  if(request.mode==='navigate'){
    event.respondWith(fetch(request).then(function(response){
      const copy=response.clone();
      caches.open(CACHE_NAME).then(function(cache){ cache.put(request,copy); });
      return response;
    }).catch(function(){ return caches.match(request).then(function(cached){
      return cached || caches.match('./Kaizen-Life-Foco.html');
    }); }));
    return;
  }
  event.respondWith(caches.match(request).then(function(cached){
    if(cached) return cached;
    return fetch(request).then(function(response){
      if(response.ok && url.origin===self.location.origin){
        const copy=response.clone();
        caches.open(CACHE_NAME).then(function(cache){ cache.put(request,copy); });
      }
      return response;
    });
  }));
});

self.addEventListener('push', function(event){
  let data={};
  try{ data=event.data ? event.data.json() : {}; }catch(error){ data={body:event.data.text()}; }
  event.waitUntil(self.registration.showNotification(data.title||'Kaizen Life',{
    body:data.body||'Você tem uma nova atualização.',
    icon:'./kaizen-icon-192.png',
    badge:'./kaizen-icon-192.png',
    tag:data.tag||data.type||'kaizen',
    renotify:false,
    data:{url:data.url||'./Kaizen-Life-Foco.html'}
  }));
});

self.addEventListener('notificationclick', function(event){
  event.notification.close();
  const target=new URL(event.notification.data.url||'./Kaizen-Life-Foco.html',self.location.origin).href;
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(function(clients){
    for(const client of clients){
      if('focus' in client){ client.navigate(target); return client.focus(); }
    }
    return self.clients.openWindow ? self.clients.openWindow(target) : null;
  }));
});
