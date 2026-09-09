const fs = require('fs');
const vm = require('vm');
const { webcrypto } = require('crypto');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const html = fs.readFileSync('Kaizen-Life-Foco.html', 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert(match, 'Bloco JavaScript não encontrado');

const listeners = {};
const elements = {
  app: { innerHTML: '' },
  'particles-overlay': { appendChild() {} },
  'toast-root': { appendChild() {} }
};
const rootVars = {};
const navigatorMock = { onLine: true };
const documentMock = {
  readyState: 'loading',
  documentElement: {
    dataset: {},
    style: { setProperty(name, value) { rootVars[name] = value; } }
  },
  addEventListener(type, listener) { listeners[type] = listener; },
  getElementById(id) { return elements[id] || null; },
  querySelector() { return null; },
  createElement() {
    return {
      className: '',
      style: { setProperty() {} },
      appendChild() {},
      remove() {},
      set textContent(value) {
        this._text = String(value ?? '');
        this.innerHTML = this._text
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
      },
      get textContent() { return this._text || ''; }
    };
  }
};

const localData = new Map();
const context = {
  console,
  elements,
  rootVars,
  document: documentMock,
  window: {
    storage: null,
    crypto: webcrypto,
    indexedDB: null,
    navigator: navigatorMock,
    location: { protocol: 'file:', origin: 'null', pathname: '/Kaizen-Life-Foco.html', href: 'file:///Kaizen-Life-Foco.html' },
    addEventListener() {},
    confirm() { return true; },
    localStorage: {
      getItem(key) { return localData.has(key) ? localData.get(key) : null; },
      setItem(key, value) { localData.set(key, String(value)); },
      removeItem(key) { localData.delete(key); }
    },
    scrollTo() {}
  },
  navigator: navigatorMock,
  setTimeout() { return 1; },
  clearTimeout() {},
  setInterval() { return 1; },
  clearInterval() {},
  requestAnimationFrame() { return 1; },
  Date,
  Math,
  Set,
  Map,
  Array,
  Object,
  Number,
  String,
  JSON,
  parseInt,
  parseFloat,
  Promise
};
context.crypto = webcrypto;
context.TextEncoder = TextEncoder;
context.globalThis = context;
vm.createContext(context);

const testsInsideApp = `
  state = hydrateProfile('test-profile', createDemoProfile());
  session.view = 'app';
  session.activeId = state.id;
  session.profiles = [];
  const focusHtml = pageFocus();
  const initialStats = focusStats();
  const initialHealth = focusHealthScore();
  const initialXp = state.xp;
  const requiredThemeVars = ['--bg','--card','--card-secondary','--card-premium','--text','--text-secondary','--green','--blue','--gold','--purple-cyber','--purple-neon','--purple-glow','--danger'];
  const newThemeIds = ['eclipseCarmesim','florestaAncestral','nevoaArtica','cafeNoir','synthwaveSunset','solarPunk','indigoMeiaNoite','pergaminhoZen','jadeImperial','nebulosaCosmica'];
  const newWallpaperIds = ['wp_topografia','wp_chuva_digital','wp_synthwave','wp_floresta_bio','wp_oceano_abissal','wp_tempestade_cosmica','wp_cristal','wp_portal_eclipse','wp_escamas_dragao','wp_reino_dourado'];
  const themeVarSetsComplete = Object.keys(THEMES).every(function(key){
    return requiredThemeVars.every(function(variable){ return !!THEMES[key].vars[variable]; });
  });
  const themeTextContrast = Object.keys(THEMES).every(function(key){
    const vars=THEMES[key].vars;
    const foreground=colorLuminance(vars['--text']);
    const background=colorLuminance(vars['--bg']);
    const ratio=(Math.max(foreground,background)+0.05)/(Math.min(foreground,background)+0.05);
    return ratio>=4.5;
  });
  const themeSecondaryContrast = Object.keys(THEMES).every(function(key){
    const vars=THEMES[key].vars;
    const foreground=colorLuminance(vars['--text-secondary']);
    const background=colorLuminance(vars['--bg']);
    const ratio=(Math.max(foreground,background)+0.05)/(Math.min(foreground,background)+0.05);
    return ratio>=4.5;
  });
  const wallpaperFieldsComplete = WALLPAPERS.every(function(w){
    return ['id','name','price','rarity','desc','layer','size','position','repeat'].every(function(field){ return w[field]!==undefined && w[field]!==''; });
  });
  const wallpaperIdsUnique = new Set(WALLPAPERS.map(function(w){ return w.id; })).size===WALLPAPERS.length;
  const wallpaperRarities = WALLPAPERS.reduce(function(acc,w){ acc[w.rarity]=(acc[w.rarity]||0)+1; return acc; },{});
  const wallpapersThemeAdaptive = WALLPAPERS.every(function(w){ return w.layer.includes('var(--'); });

  function click(action, extra){
    const dataset = Object.assign({action:action}, extra || {});
    document._click({
      target:{ closest:function(){ return {dataset:dataset}; } },
      preventDefault:function(){},
      clientX:0,
      clientY:0
    });
  }

  click('toggle-focus-ritual',{key:'phone'});
  click('toggle-focus-ritual',{key:'notifications'});
  click('start-focus-timer');
  const timerStarted = state.focusProject.timer.running;
  click('pause-focus-timer');
  const timerPaused = !state.focusProject.timer.running;
  click('toggle-focus-milestone',{id:'fm2'});
  const milestoneRewarded = state.xp === initialXp + 25;

  const appHtml=buildAppHTML();
  const storeHtml=pageStore();
  const unifiedMobileTriggerCount=(appHtml.match(/data-action="toggle-mobile-menu"/g)||[]).length;
  const topbarHasNoMenuTrigger=!appHtml.includes('mobile-menu-trigger');
  const mobileShellHtml=buildMobileNavigation();
  const mobileGridStart=mobileShellHtml.indexOf('<nav class="mobile-nav-grid"');
  const mobileGridEnd=mobileShellHtml.indexOf('</nav>',mobileGridStart);
  const mobileGridHtml=mobileGridStart>=0 && mobileGridEnd>mobileGridStart ? mobileShellHtml.slice(mobileGridStart,mobileGridEnd) : '';
  const allPagesInMobileMenu=NAV_ITEMS.every(function(item){ return mobileGridHtml.includes('data-page="'+item.page+'"'); });
  const mobileMenuLinkCount=(mobileGridHtml.match(/class="mobile-nav-link/g)||[]).length;
  const mobileHasSingleFab=mobileShellHtml.includes('id="mobile-nav-fab"') && !mobileShellHtml.includes('id="bottom-nav"') && !mobileShellHtml.includes('class="bn-item');
  const allPagesRender=NAV_ITEMS.every(function(item){ state.currentPage=item.page; return buildPageContent().trim().length>100; });
  state.currentPage='dashboard';
  click('toggle-mobile-menu');
  const mobileMenuOpens=session.mobileMenuOpen && document.getElementById('app').innerHTML.includes('id="mobile-nav-layer" class="open"');
  const mobileFabBecomesClose=document.getElementById('app').innerHTML.includes('id="mobile-nav-fab" class="open"') && document.getElementById('app').innerHTML.includes('<span>Fechar</span>');
  click('nav',{page:'reports'});
  const mobileMenuRoutes=state.currentPage==='reports' && !session.mobileMenuOpen;
  click('toggle-mobile-menu');
  click('close-mobile-menu');
  const mobileMenuCloses=!session.mobileMenuOpen;
  state.currentPage='dashboard';
  renderApp();
  applyTheme('pergaminhoZen');
  applyWallpaper('wp_portal_eclipse');
  state.equipped.wallpaper='wp_portal_eclipse';

  const habitCountBefore=state.habits.length;
  elements.newHabitInput={value:'Respiração consciente'};
  elements.newHabitTimeInput={value:'07:30'};
  elements.newHabitCategory={value:'Saúde Mental'};
  click('add-habit');
  const createdHabit=state.habits[state.habits.length-1];
  const habitCreated=state.habits.length===habitCountBefore+1 && createdHabit.name==='Respiração consciente';
  const habitHasDeleteControl=pageHabits().includes('data-entity="habit"');
  click('ask-delete-entity',{entity:'habit',id:createdHabit.id});
  const habitConfirmationVisible=pageHabits().includes('Excluir o hábito');
  click('confirm-delete-entity',{entity:'habit',id:createdHabit.id});
  const habitDeleted=state.habits.length===habitCountBefore && !state.habits.some(function(h){return h.id===createdHabit.id;});

  const taskCountBefore=state.tasks.length;
  elements.newTaskInput={value:'Revisar o fluxo CRUD'};
  click('add-task');
  const createdTask=state.tasks[0];
  const taskCreated=state.tasks.length===taskCountBefore+1 && createdTask.title==='Revisar o fluxo CRUD';
  const taskHasDeleteControl=pageTasks().includes('data-entity="task"');
  click('ask-delete-entity',{entity:'task',id:createdTask.id});
  const taskConfirmationVisible=pageTasks().includes('Excluir a tarefa');
  click('confirm-delete-entity',{entity:'task',id:createdTask.id});
  const taskDeleted=state.tasks.length===taskCountBefore && !state.tasks.some(function(task){return task.id===createdTask.id;});

  const goalCountBefore=state.goals.length;
  elements.newGoalInput={value:'Concluir o CRUD do Kaizen'};
  elements.newGoalTerm={value:'Semanal'};
  elements.newGoalCategory={value:'Trabalho'};
  click('add-goal');
  const createdGoal=state.goals[state.goals.length-1];
  const goalCreated=state.goals.length===goalCountBefore+1 && createdGoal.text==='Concluir o CRUD do Kaizen';
  const goalHasDeleteControl=pageGoals().includes('data-entity="goal"');
  click('ask-delete-entity',{entity:'goal',id:createdGoal.id});
  const goalConfirmationVisible=pageGoals().includes('Excluir a meta');
  click('confirm-delete-entity',{entity:'goal',id:createdGoal.id});
  const goalDeleted=state.goals.length===goalCountBefore && !state.goals.some(function(goal){return goal.id===createdGoal.id;});

  const focusXpBeforeDelete=state.xp;
  const focusCoinsBeforeDelete=state.coins;
  const focusHasReplacementControl=pageFocus().includes('data-entity="focus"') && pageFocus().includes('Encerrar / novo foco');
  click('ask-delete-entity',{entity:'focus'});
  const focusConfirmationVisible=pageFocus().includes('Encerrar este Projeto Central?');
  click('confirm-delete-entity',{entity:'focus'});
  const focusDeleted=!state.focusProject.active && state.focusProject.sessions.length===0 && state.focusProject.milestones.length===0;
  const focusFormOpened=pageFocus().includes('Ativar Projeto Central');
  const focusDeletePreservesRewards=state.xp===focusXpBeforeDelete && state.coins===focusCoinsBeforeDelete;
  elements.focusNameInput={value:'Construir a próxima versão do Kaizen'};
  elements.focusIdentityInput={value:'Sou alguém que termina sistemas úteis.'};
  elements.focusWhyInput={value:'Quero transformar intenção em uma entrega real.'};
  elements.focusOutcomeInput={value:'Publicar uma versão utilizável e testada.'};
  elements.focusDailyInput={value:'60'};
  elements.focusCycleInput={value:'50'};
  elements.focusBreakInput={value:'10'};
  elements.focusDaysInput={value:'90'};
  elements.focusNextInput={value:'Implementar o próximo fluxo completo.'};
  elements.focusQuestionInput={value:'Qual é o menor incremento testável?'};
  click('save-focus-project');
  const focusRecreated=state.focusProject.active && state.focusProject.name==='Construir a próxima versão do Kaizen';
  const focusRewardCannotBeFarmed=state.xp===focusXpBeforeDelete && state.coins===focusCoinsBeforeDelete;

  const weakPasswordRejected=!passwordStrength('kaizen123').valid;
  const strongPasswordAccepted=passwordStrength('Kaizen#2026Muito').valid;
  const emailNormalizationWorks=normalizeEmail('  Miranda@Exemplo.COM ')==='miranda@exemplo.com' && isValidEmail('miranda@exemplo.com');
  const phoneNormalizationWorks=normalizePhone('(11) 99999-9999')==='+5511999999999' && isValidPhone('(11) 99999-9999');
  session.authError=''; session.authNotice=''; session.authBusy=false; session.authReturn=null; session.pendingAuth=null;
  session.authScreen='login'; session.view='picker';
  session.profiles=[
    {id:state.id,name:state.name,level:getLevel(state.xp),emoji:'🙂',auth:{method:'email',email:'miranda@exemplo.com',passwordSalt:'salt',passwordHash:'hash',verified:true}},
    {id:'legacy-test',name:'Conta antiga',level:3,emoji:'🌱'}
  ];
  session.activeId=state.id;
  const loginAuthHtml=renderPicker();
  session.authScreen='register';
  const registerAuthHtml=renderPicker();
  session.authScreen='google';
  const googleAuthHtml=renderPicker();
  session.authScreen='phone'; session.pendingAuth={method:'phone',phone:'+5511999999999',name:'Miranda',code:'123456'};
  const phoneOtpHtml=renderPicker();
  session.pendingAuth=null; session.authScreen='recovery'; session.recoveryMethod='email';
  const recoveryStartHtml=renderPicker();
  session.pendingAuth={purpose:'recovery',stage:'code',channel:'email',accountId:state.id,destination:'mi***@exemplo.com',code:'123456'};
  const recoveryCodeHtml=renderPicker();
  session.pendingAuth.stage='reset';
  const recoveryResetHtml=renderPicker();
  session.pendingAuth=null; session.authScreen='login'; session.view='app';
  const accountCardHtml=accountAccessCardHTML(true);
  const profileAccountHtml=pageProfile();
  const settingsAccountHtml=pageSettings();
  const loginMethodsPresent=loginAuthHtml.includes('auth-login-email') && loginAuthHtml.includes('data-screen="google"') && loginAuthHtml.includes('data-screen="phone"');
  const knownAccountSwitcherPresent=loginAuthHtml.includes('auth-select-account') && loginAuthHtml.includes('CONTAS NESTE DISPOSITIVO');
  const legacyMigrationPresent=loginAuthHtml.includes('auth-use-legacy') && loginAuthHtml.includes('Conta antiga');
  const strongPasswordUiPresent=registerAuthHtml.includes('data-password-strength="true"') && registerAuthHtml.includes('12 ou mais caracteres') && registerAuthHtml.includes('Criar conta segura');
  const registerProvidersPresent=registerAuthHtml.includes('data-screen="google"') && registerAuthHtml.includes('data-screen="phone"');
  const googlePrototypeHonest=googleAuthHtml.includes('OAuth') && googleAuthHtml.includes('Continuar no protótipo');
  const phoneOtpFlowPresent=phoneOtpHtml.includes('auth-phone-verify') && phoneOtpHtml.includes('123456') && phoneOtpHtml.includes('one-time-code');
  const forgotPasswordEntryPresent=loginAuthHtml.includes('Esqueci minha senha') && loginAuthHtml.includes('data-screen="recovery"');
  const recoveryMethodsPresent=recoveryStartHtml.includes('data-method="email"') && recoveryStartHtml.includes('data-method="phone"') && recoveryStartHtml.includes('auth-recovery-send');
  const recoveryCodeFlowPresent=recoveryCodeHtml.includes('auth-recovery-verify') && recoveryCodeHtml.includes('123456');
  const recoveryStrongResetPresent=recoveryResetHtml.includes('auth-recovery-reset') && recoveryResetHtml.includes('data-password-strength="true"');
  const accountMenuIntegrated=accountCardHtml.includes('manage-account-security') && accountCardHtml.includes('add-account') && accountCardHtml.includes('switch-account');
  const accountMenuInBothPages=profileAccountHtml.includes('CONTA E ACESSO') && settingsAccountHtml.includes('CONTA E ACESSO');
  const passwordNotSerializedWithProfile=!Object.prototype.hasOwnProperty.call(serializeProfile(state),'passwordHash') && !Object.prototype.hasOwnProperty.call(serializeProfile(state),'auth');

  const stateBeforeGuide=state;
  const profilesBeforeGuide=session.profiles.slice();
  const activeBeforeGuide=session.activeId;
  state=hydrateProfile('guide-test',createEmptyProfile('Novo usuário'));
  session.activeId=state.id; session.profiles=[]; session.view='app';
  const newUserHelpChoice=buildHelpExperience();
  click('help-opt-in',{enabled:'true'});
  const dashboardHelpFloat=buildHelpExperience();
  click('help-next');
  const helpMovesToNext=state.currentPage==='focus' && state.helpGuide.seenPages.includes('dashboard') && buildHelpExperience().includes(HELP_TIPS.focus.title);
  const guidePersists=Object.prototype.hasOwnProperty.call(serializeProfile(state),'helpGuide');
  state.currentPage='settings';
  const helpSettingsControls=pageSettings().includes('toggle-help-guide') && pageSettings().includes('restart-help-guide');
  state=stateBeforeGuide; session.profiles=profilesBeforeGuide; session.activeId=activeBeforeGuide; session.view='app';
  const newUserOptInPresent=newUserHelpChoice.includes('Quer uma ajuda para conhecer o Kaizen?') && newUserHelpChoice.includes('data-action="help-opt-in"');
  const contextualHelpPresent=dashboardHelpFloat.includes(HELP_TIPS.dashboard.title) && dashboardHelpFloat.includes('help-dismiss') && dashboardHelpFloat.includes('help-next') && dashboardHelpFloat.includes('help-disable');
  const everyPageHasHelp=NAV_ITEMS.length===10 && NAV_ITEMS.every(function(item){return HELP_TIPS[item.page] && HELP_TIPS[item.page].title && HELP_TIPS[item.page].body;});
  globalThis.__result = {
    focusHtml:focusHtml,
    timerStarted:timerStarted,
    timerPaused:timerPaused,
    milestoneRewarded:milestoneRewarded,
    todayMinutes:initialStats.todayMinutes,
    healthScore:initialHealth.score,
    serializedHasFocus:Object.prototype.hasOwnProperty.call(serializeProfile(state),'focusProject'),
    appHtml:appHtml,
    themeCount:Object.keys(THEMES).length,
    themeOrderCount:THEME_ORDER.length,
    newThemesPresent:newThemeIds.every(function(key){ return !!THEMES[key] && THEME_ORDER.includes(key); }),
    themeVarSetsComplete:themeVarSetsComplete,
    themeTextContrast:themeTextContrast,
    themeSecondaryContrast:themeSecondaryContrast,
    storeHasNewThemes:newThemeIds.every(function(key){ return storeHtml.includes(THEMES[key].name); }),
    wallpaperCount:WALLPAPERS.length,
    newWallpapersPresent:newWallpaperIds.every(function(id){ return WALLPAPERS.some(function(w){ return w.id===id; }); }),
    storeHasNewWallpapers:newWallpaperIds.every(function(id){ const w=WALLPAPERS.find(function(item){ return item.id===id; }); return w && storeHtml.includes(w.name); }),
    wallpaperFieldsComplete:wallpaperFieldsComplete,
    wallpaperIdsUnique:wallpaperIdsUnique,
    wallpapersThemeAdaptive:wallpapersThemeAdaptive,
    epicWallpaperCount:wallpaperRarities.epico||0,
    legendaryWallpaperCount:wallpaperRarities.lendario||0,
    wallpaperApplied:document.documentElement.dataset.wallpaper==='wp_portal_eclipse' && rootVars['--wallpaper-layer']===WALLPAPERS.find(function(w){ return w.id==='wp_portal_eclipse'; }).layer,
    wallpaperPersists:serializeProfile(state).equipped.wallpaper==='wp_portal_eclipse',
    allPagesInMobileMenu:allPagesInMobileMenu,
    mobileMenuLinkCount:mobileMenuLinkCount,
    mobileHasSingleFab:mobileHasSingleFab,
    unifiedMobileTriggerCount:unifiedMobileTriggerCount,
    topbarHasNoMenuTrigger:topbarHasNoMenuTrigger,
    mobileMenuOpens:mobileMenuOpens,
    mobileFabBecomesClose:mobileFabBecomesClose,
    mobileMenuRoutes:mobileMenuRoutes,
    mobileMenuCloses:mobileMenuCloses,
    allPagesRender:allPagesRender,
    habitCreated:habitCreated,
    habitHasDeleteControl:habitHasDeleteControl,
    habitConfirmationVisible:habitConfirmationVisible,
    habitDeleted:habitDeleted,
    taskCreated:taskCreated,
    taskHasDeleteControl:taskHasDeleteControl,
    taskConfirmationVisible:taskConfirmationVisible,
    taskDeleted:taskDeleted,
    goalCreated:goalCreated,
    goalHasDeleteControl:goalHasDeleteControl,
    goalConfirmationVisible:goalConfirmationVisible,
    goalDeleted:goalDeleted,
    focusHasReplacementControl:focusHasReplacementControl,
    focusConfirmationVisible:focusConfirmationVisible,
    focusDeleted:focusDeleted,
    focusFormOpened:focusFormOpened,
    focusDeletePreservesRewards:focusDeletePreservesRewards,
    focusRecreated:focusRecreated,
    focusRewardCannotBeFarmed:focusRewardCannotBeFarmed,
    weakPasswordRejected:weakPasswordRejected,
    strongPasswordAccepted:strongPasswordAccepted,
    emailNormalizationWorks:emailNormalizationWorks,
    phoneNormalizationWorks:phoneNormalizationWorks,
    loginMethodsPresent:loginMethodsPresent,
    knownAccountSwitcherPresent:knownAccountSwitcherPresent,
    legacyMigrationPresent:legacyMigrationPresent,
    strongPasswordUiPresent:strongPasswordUiPresent,
    registerProvidersPresent:registerProvidersPresent,
    googlePrototypeHonest:googlePrototypeHonest,
    phoneOtpFlowPresent:phoneOtpFlowPresent,
    forgotPasswordEntryPresent:forgotPasswordEntryPresent,
    recoveryMethodsPresent:recoveryMethodsPresent,
    recoveryCodeFlowPresent:recoveryCodeFlowPresent,
    recoveryStrongResetPresent:recoveryStrongResetPresent,
    accountMenuIntegrated:accountMenuIntegrated,
    accountMenuInBothPages:accountMenuInBothPages,
    passwordNotSerializedWithProfile:passwordNotSerializedWithProfile,
    newUserOptInPresent:newUserOptInPresent,
    contextualHelpPresent:contextualHelpPresent,
    everyPageHasHelp:everyPageHasHelp,
    helpMovesToNext:helpMovesToNext,
    guidePersists:guidePersists,
    helpSettingsControls:helpSettingsControls,
    lightThemeDetected:document.documentElement.dataset.themeMode==='light',
    derivedThemeTokens:!!rootVars['--on-accent'] && !!rootVars['--border'] && !!rootVars['--text-muted']
  };
`;

documentMock._click = null;
const originalAddEventListener = documentMock.addEventListener.bind(documentMock);
documentMock.addEventListener = function(type, listener) {
  originalAddEventListener(type, listener);
  if (type === 'click') documentMock._click = listener;
};

vm.runInContext(match[1] + testsInsideApp, context, { timeout: 5000 });
const result = context.__result;

assert(result.focusHtml.includes('SESSÃO DE FOCO PROFUNDO'), 'Página de foco não foi renderizada');
assert(result.focusHtml.includes('PAINEL DE CAPACIDADE'), 'Painel de saúde não foi renderizado');
assert(result.timerStarted, 'Cronômetro não iniciou');
assert(result.timerPaused, 'Cronômetro não pausou');
assert(result.milestoneRewarded, 'Marco não concedeu XP corretamente');
assert(result.todayMinutes === 60, 'Sessões de demonstração não foram contabilizadas');
assert(result.healthScore >= 65, 'Score de saúde saudável foi calculado incorretamente');
assert(result.serializedHasFocus, 'Projeto Central não está na persistência');
assert(result.appHtml.includes('data-page="focus"'), 'Navegação para foco não foi integrada');
assert(result.themeCount === 22, 'Quantidade total de temas incorreta');
assert(result.themeOrderCount === 21, 'Quantidade de temas desbloqueáveis incorreta');
assert(result.newThemesPresent, 'Um ou mais dos 10 novos temas não foi integrado');
assert(result.themeVarSetsComplete, 'Um ou mais temas está com variáveis incompletas');
assert(result.themeTextContrast, 'Um ou mais temas não possui contraste mínimo no texto principal');
assert(result.themeSecondaryContrast, 'Um ou mais temas não possui contraste mínimo no texto secundário');
assert(result.storeHasNewThemes, 'Um ou mais dos 10 novos temas não aparece na loja');
assert(result.wallpaperCount === 20, 'Quantidade total de wallpapers incorreta');
assert(result.newWallpapersPresent, 'Um ou mais dos 10 novos wallpapers não foi integrado');
assert(result.storeHasNewWallpapers, 'Um ou mais dos 10 novos wallpapers não aparece na loja');
assert(result.wallpaperFieldsComplete, 'Um ou mais wallpapers está com dados incompletos');
assert(result.wallpaperIdsUnique, 'Existem IDs duplicados no catálogo de wallpapers');
assert(result.wallpapersThemeAdaptive, 'Um ou mais wallpapers não acompanha as variáveis do tema');
assert(result.epicWallpaperCount >= 7, 'Catálogo não possui wallpapers épicos suficientes');
assert(result.legendaryWallpaperCount >= 3, 'Catálogo não possui wallpapers lendários suficientes');
assert(result.wallpaperApplied, 'Aplicação visual do wallpaper falhou');
assert(result.wallpaperPersists, 'Wallpaper equipado não foi persistido');
assert(result.allPagesInMobileMenu, 'Uma ou mais páginas não está acessível no menu móvel');
assert(result.mobileMenuLinkCount === 10, 'Menu móvel não possui as 10 páginas do desktop');
assert(result.mobileHasSingleFab, 'A barra inferior antiga ainda existe ou o botão flutuante está ausente');
assert(result.unifiedMobileTriggerCount === 1, 'A interface móvel ainda possui gatilhos de menu redundantes');
assert(result.topbarHasNoMenuTrigger, 'O botão redundante do topo ainda está presente');
assert(result.mobileMenuOpens, 'Menu móvel não abre corretamente');
assert(result.mobileFabBecomesClose, 'Botão flutuante não muda para o estado de fechamento');
assert(result.mobileMenuRoutes, 'Navegação pelo menu móvel falhou');
assert(result.mobileMenuCloses, 'Menu móvel não fecha corretamente');
assert(result.allPagesRender, 'Uma ou mais páginas falhou ao renderizar durante a auditoria responsiva');
assert(result.habitCreated, 'Criação de hábito falhou');
assert(result.habitHasDeleteControl, 'Controle para excluir hábito está ausente');
assert(result.habitConfirmationVisible, 'Confirmação para excluir hábito não apareceu');
assert(result.habitDeleted, 'Exclusão de hábito falhou');
assert(result.taskCreated, 'Criação de tarefa falhou');
assert(result.taskHasDeleteControl, 'Controle para excluir tarefa está ausente');
assert(result.taskConfirmationVisible, 'Confirmação para excluir tarefa não apareceu');
assert(result.taskDeleted, 'Exclusão de tarefa falhou');
assert(result.goalCreated, 'Criação de meta falhou');
assert(result.goalHasDeleteControl, 'Controle para excluir meta está ausente');
assert(result.goalConfirmationVisible, 'Confirmação para excluir meta não apareceu');
assert(result.goalDeleted, 'Exclusão de meta falhou');
assert(result.focusHasReplacementControl, 'Ação para encerrar e trocar o Projeto Central está ausente');
assert(result.focusConfirmationVisible, 'Confirmação para encerrar o Projeto Central não apareceu');
assert(result.focusDeleted, 'Exclusão do Projeto Central não limpou seus dados');
assert(result.focusFormOpened, 'Formulário para criar um novo foco não abriu após a exclusão');
assert(result.focusDeletePreservesRewards, 'Excluir o Projeto Central removeu recompensas já conquistadas');
assert(result.focusRecreated, 'Não foi possível criar um novo Projeto Central');
assert(result.focusRewardCannotBeFarmed, 'Trocar o Projeto Central permitiu acumular o bônus inicial novamente');
assert(result.weakPasswordRejected, 'Validador aceitou uma senha fraca');
assert(result.strongPasswordAccepted, 'Validador rejeitou uma senha realmente forte');
assert(result.emailNormalizationWorks, 'Normalização ou validação de e-mail falhou');
assert(result.phoneNormalizationWorks, 'Normalização ou validação de telefone falhou');
assert(result.loginMethodsPresent, 'Um ou mais métodos de login não aparece na tela');
assert(result.knownAccountSwitcherPresent, 'Tela de troca não lista as contas conhecidas do dispositivo');
assert(result.legacyMigrationPresent, 'Contas antigas ficaram sem rota de migração');
assert(result.strongPasswordUiPresent, 'Interface de senha forte está incompleta');
assert(result.registerProvidersPresent, 'Cadastro não oferece Google e telefone');
assert(result.googlePrototypeHonest, 'Fluxo Google não informa corretamente sua condição de protótipo');
assert(result.phoneOtpFlowPresent, 'Fluxo de código telefônico está incompleto');
assert(result.forgotPasswordEntryPresent, 'Link de esqueci minha senha está ausente');
assert(result.recoveryMethodsPresent, 'Recuperação não oferece e-mail e telefone');
assert(result.recoveryCodeFlowPresent, 'Verificação do código de recuperação está incompleta');
assert(result.recoveryStrongResetPresent, 'Redefinição não exige uma nova senha forte');
assert(result.accountMenuIntegrated, 'Gerenciamento de conta não foi integrado');
assert(result.accountMenuInBothPages, 'Gerenciamento de conta não aparece em Perfil e Configurações');
assert(result.passwordNotSerializedWithProfile, 'Credencial foi misturada aos dados comuns do perfil');
assert(result.newUserOptInPresent, 'Novo usuário não recebe a escolha inicial sobre as dicas');
assert(result.contextualHelpPresent, 'Mensagem flutuante contextual está incompleta');
assert(result.everyPageHasHelp, 'Uma ou mais telas não possui mensagem de ajuda própria');
assert(result.helpMovesToNext, 'Guia não avança corretamente entre as telas');
assert(result.guidePersists, 'Preferências do guia não entram na persistência do perfil');
assert(result.helpSettingsControls, 'Configurações não permitem controlar ou reiniciar o guia');
assert(result.lightThemeDetected, 'Detecção automática de tema claro falhou');
assert(result.derivedThemeTokens, 'Tokens de contraste derivados não foram aplicados');

assert(html.includes('@media (max-width:600px)') && html.includes('.mobile-nav-grid'), 'CSS responsivo principal não foi integrado');
assert(html.includes('env(safe-area-inset-bottom)') && html.includes('#mobile-nav-fab'), 'Suporte ao botão móvel e áreas seguras ausente');
assert(html.includes("const SYNC_DB_NAME='kaizen-offline-sync'") && html.includes('enqueueOfflineMutation'), 'Fila offline persistente não foi integrada');
assert(html.includes('discard-sync-conflicts') && html.includes('Sincronizar agora'), 'Controles visuais de sincronização estão ausentes');
assert(html.includes('/auth/google/start') && html.includes('/auth/google/exchange'), 'OAuth oficial do Google não foi conectado ao frontend');

async function runAsyncAuthFlow(){
  const authResult = await vm.runInContext(`(async function(){
    function authEvent(action,extra){
      const dataset=Object.assign({action:action},extra||{});
      return {target:{closest:function(){return {dataset:dataset};}},preventDefault:function(){},clientX:0,clientY:0};
    }
    session.profiles=[];
    session.view='picker';
    session.authScreen='register';
    session.authReturn=null;
    session.pendingAuth=null;
    state=null;
    elements.authRegisterName={value:'Miranda'};
    elements.authRegisterEmail={value:'miranda@kaizen.test'};
    elements.authRegisterPassword={value:'Kaizen#2026Muito'};
    elements.authRegisterConfirm={value:'Kaizen#2026Muito'};
    await document._click(authEvent('auth-register-email'));
    const createdId=session.activeId;
    const createdEntry=session.profiles.find(function(account){return account.id===createdId;});
    const created={
      active:session.view==='app' && !!state,
      method:createdEntry && createdEntry.auth && createdEntry.auth.method,
      hashExists:!!(createdEntry && createdEntry.auth && createdEntry.auth.passwordHash),
      rawPasswordAbsent:JSON.stringify(createdEntry).indexOf('Kaizen#2026Muito')===-1
    };
    await document._click(authEvent('switch-account'));
    elements.authLoginEmail={value:'miranda@kaizen.test'};
    elements.authLoginPassword={value:'senha-errada'};
    await document._click(authEvent('auth-login-email'));
    const wrongPasswordBlocked=session.view==='picker' && !!session.authError;
    elements.authLoginEmail={value:'miranda@kaizen.test'};
    elements.authLoginPassword={value:'Kaizen#2026Muito'};
    await document._click(authEvent('auth-login-email'));
    const correctPasswordEnters=session.view==='app' && session.activeId===createdId && !!state;
    await document._click(authEvent('switch-account'));
    session.authScreen='recovery'; session.recoveryMethod='email'; renderApp();
    elements.authRecoveryIdentifier={value:'miranda@kaizen.test'};
    await document._click(authEvent('auth-recovery-send'));
    const recoveryCodePrepared=!!session.pendingAuth && session.pendingAuth.purpose==='recovery' && session.pendingAuth.channel==='email';
    elements.authRecoveryCode={value:'123456'};
    await document._click(authEvent('auth-recovery-verify'));
    const recoveryReachedReset=!!session.pendingAuth && session.pendingAuth.stage==='reset';
    elements.authRecoveryPassword={value:'Kaizen#2027Novo'};
    elements.authRecoveryConfirm={value:'Kaizen#2027Novo'};
    await document._click(authEvent('auth-recovery-reset'));
    const emailRecoveryWorks=session.view==='app' && session.activeId===createdId;
    await document._click(authEvent('switch-account'));
    elements.authLoginEmail={value:'miranda@kaizen.test'};
    elements.authLoginPassword={value:'Kaizen#2026Muito'};
    await document._click(authEvent('auth-login-email'));
    const oldPasswordInvalidAfterRecovery=session.view==='picker' && !!session.authError;
    elements.authLoginEmail={value:'miranda@kaizen.test'};
    elements.authLoginPassword={value:'Kaizen#2027Novo'};
    await document._click(authEvent('auth-login-email'));
    const newPasswordValidAfterRecovery=session.view==='app' && session.activeId===createdId;
    await document._click(authEvent('switch-account'));
    session.authScreen='google'; renderApp();
    elements.authGoogleName={value:'Miranda Google'};
    elements.authGoogleEmail={value:'miranda.google@gmail.com'};
    await document._click(authEvent('auth-google-continue'));
    const googleEntry=session.profiles.find(function(account){return account.auth && account.auth.email==='miranda.google@gmail.com';});
    const googleFlowWorks=session.view==='app' && googleEntry && googleEntry.auth.method==='google';
    await document._click(authEvent('switch-account'));
    session.authScreen='phone'; renderApp();
    elements.authPhoneName={value:'Miranda Telefone'};
    elements.authPhoneNumber={value:'(11) 98888-7777'};
    await document._click(authEvent('auth-phone-send'));
    const phoneCodeRequested=!!session.pendingAuth && session.pendingAuth.phone==='+5511988887777';
    elements.authPhoneCode={value:'123456'};
    await document._click(authEvent('auth-phone-verify'));
    const phoneEntry=session.profiles.find(function(account){return account.auth && account.auth.phone==='+5511988887777';});
    const phoneFlowWorks=session.view==='app' && !!phoneEntry && phoneEntry.auth.method==='phone';
    await document._click(authEvent('switch-account'));
    session.authScreen='recovery'; session.recoveryMethod='phone'; renderApp();
    elements.authRecoveryIdentifier={value:'(11) 98888-7777'};
    await document._click(authEvent('auth-recovery-send'));
    const phoneRecoveryCodePrepared=!!session.pendingAuth && session.pendingAuth.channel==='phone';
    elements.authRecoveryCode={value:'123456'};
    await document._click(authEvent('auth-recovery-verify'));
    return {
      created:created,
      wrongPasswordBlocked:wrongPasswordBlocked,
      correctPasswordEnters:correctPasswordEnters,
      recoveryCodePrepared:recoveryCodePrepared,
      recoveryReachedReset:recoveryReachedReset,
      emailRecoveryWorks:emailRecoveryWorks,
      oldPasswordInvalidAfterRecovery:oldPasswordInvalidAfterRecovery,
      newPasswordValidAfterRecovery:newPasswordValidAfterRecovery,
      googleFlowWorks:!!googleFlowWorks,
      phoneCodeRequested:phoneCodeRequested,
      phoneFlowWorks:phoneFlowWorks,
      phoneRecoveryCodePrepared:phoneRecoveryCodePrepared,
      phoneRecoveryWorks:session.view==='app' && session.activeId===phoneEntry.id
    };
  })()`, context, {timeout:5000});
  assert(authResult.created.active, 'Cadastro por e-mail não abriu a nova conta');
  assert(authResult.created.method==='email', 'Cadastro não registrou o método de autenticação');
  assert(authResult.created.hashExists && authResult.created.rawPasswordAbsent, 'Senha não foi protegida por hash local');
  assert(authResult.wrongPasswordBlocked, 'Login aceitou uma senha incorreta');
  assert(authResult.correctPasswordEnters, 'Login rejeitou a senha correta');
  assert(authResult.recoveryCodePrepared && authResult.recoveryReachedReset, 'Recuperação por e-mail não chegou à redefinição');
  assert(authResult.emailRecoveryWorks, 'Recuperação por e-mail não reabriu a conta');
  assert(authResult.oldPasswordInvalidAfterRecovery, 'Senha antiga continuou válida após a recuperação');
  assert(authResult.newPasswordValidAfterRecovery, 'Nova senha foi rejeitada após a recuperação');
  assert(authResult.googleFlowWorks, 'Fluxo de conta Google do protótipo falhou');
  assert(authResult.phoneCodeRequested, 'Fluxo telefônico não preparou a verificação');
  assert(authResult.phoneFlowWorks, 'Fluxo de conta por telefone falhou');
  assert(authResult.phoneRecoveryCodePrepared && authResult.phoneRecoveryWorks, 'Recuperação por telefone falhou');
  console.log('JavaScript + estado + temas + wallpapers + mobile + CRUD + autenticação: OK');
}

runAsyncAuthFlow().catch(function(error){
  console.error(error.stack || error);
  process.exitCode=1;
});
