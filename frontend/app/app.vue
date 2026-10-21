<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
const { status } = useAuth()
const { startTour, stopTour, isOnboardingActive } = useOnboarding() 


// 1. Richiama la configurazione globale dell'app
const appConfig = useAppConfig()
const route = useRoute()

const applyTheme = (currentPath) => {
  if (currentPath === '/') {
    // Se siamo nella schermata di login/signup, forziamo il verde di default
    appConfig.ui.colors.primary = 'green'
  } else {
    // Nelle altre pagine dell'app, applichiamo il colore scelto dall'utente
    const savedTheme = localStorage.getItem('duosigna-theme')
    if (savedTheme) {
      appConfig.ui.colors.primary = savedTheme
    }
  }
}


onMounted(() => {
  applyTheme(route.path)

  // Osserva i futuri cambi di pagina e aggiorna il colore dinamicamente
  watch(() => route.path, (newPath) => {
    applyTheme(newPath)
  })
})


useHead({
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' }
  ],
  htmlAttrs: {
    lang: 'en'
  }
})

const title = 'DuoSigna'
const description = 'Learn sign language with DuoSigna, the interactive platform for mastering sign language through engaging lessons, real-time feedback, and a supportive community. Start your journey to fluency today!'

</script>

<template>
  <UApp>
    <UHeader :ui="{ container: 'max-w-full px-4 sm:px-6 lg:px-8' }">
      
      <template #left>
        <div class="flex items-center gap-3">
          
          <NuxtLink 
            v-if="status === 'authenticated'" 
            to="/homepage" 
            class="text-2xl font-extrabold text-primary-600 dark:text-primary-400 tracking-tight hover:opacity-80 transition-all"
          >
            DuoSigna
          </NuxtLink>
          
          <span 
            v-else 
            class="text-2xl font-extrabold text-green-600 dark:text-primary-400 tracking-tight"
          >
            DuoSigna
          </span>

        </div>
      </template>

      <template #panel>
        <div class="hidden"></div>
      </template>
      
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>

    <USeparator icon="i-simple-icons-nuxtdotjs" />

  </UApp>
</template>

<style>

header button.lg\:hidden {
  display: none !important;
}
</style>