<template>
  <div>
    <div class="flex min-h-[calc(100vh-140px)] bg-white dark:bg-transparent transition-colors duration-200">
      
      <AppSidebar />

      <div class="flex-1 px-4 lg:px-8 py-12 lg:py-16 w-full">
        <div class="max-w-6xl mx-auto flex flex-col gap-20 lg:gap-28">
          
          <div id="tour-welcome-card" v-if="status === 'authenticated'" class="bg-primary-50 dark:bg-primary-900/20 p-6 rounded-2xl border border-primary-100 dark:border-primary-800 flex justify-between items-center">
            <div>
              <h1 class="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white">
                Welcome, {{ user?.nome }}! 👋
                <UButton 
                  icon="i-lucide-info" 
                  color="primary" 
                  variant="ghost" 
                  size="sm"
                  class="rounded-full"
                  title="Come funziona"
                  @click="startTour" 
                />
              </h1>
              
              <p class="text-gray-600 dark:text-gray-400">Ready for your sign language lesson today?</p>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wider">Your score</span>
              <p class="text-4xl font-black text-primary-600 dark:text-primary-400">{{ user?.score }}</p>
            </div>
          </div>

          <div class="flex flex-col lg:flex-row items-center w-full gap-8 lg:gap-16">        
            <UCard class="w-full lg:w-2/5 h-48 lg:h-72 flex flex-col items-center justify-center text-center shadow-lg hover:shadow-xl transition-shadow border-t-4 border-t-transparent hover:border-t-primary-500 duration-300">
              <UIcon name="i-lucide-bot" class="w-24 h-24 lg:w-40 lg:h-40 text-primary-500 mx-auto transition-colors duration-300" />
            </UCard>
            <div class="w-full lg:w-3/5 flex flex-col items-start text-left">
              <h2 class="text-3xl lg:text-5xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-4">
                Sign Tutor
              </h2>
              <p class="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed text-justify">
                Your personal AI guide for American Sign Language. Discover how to perform specific signs through video and GIF references, and use the real-time webcam recognition to test your skills and track your progress.
              </p>
              <UButton size="xl" color="primary" variant="solid" class="px-8 py-4 text-lg" to="/chatbot">
                Access Sign Tutor
              </UButton>
            </div>
          </div>

          <div class="flex flex-col lg:flex-row-reverse items-center w-full gap-8 lg:gap-16">        
            <UCard class="w-full lg:w-2/5 h-48 lg:h-72 flex flex-col items-center justify-center text-center shadow-lg hover:shadow-xl transition-shadow border-t-4 border-t-transparent hover:border-t-primary-500 duration-300">
              <UIcon name="i-lucide-book-open" class="w-24 h-24 lg:w-40 lg:h-40 text-primary-500 mx-auto transition-colors duration-300" />
            </UCard>
            <div class="w-full lg:w-3/5 flex flex-col items-start lg:items-end text-left lg:text-right">
              <h2 class="text-3xl lg:text-5xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-4">
                Dictionary
              </h2>
              <p class="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed text-justify">
                Explore the entire collection of available signs. Keep track of your progress, discover which words you have already unlocked, and review the descriptions to execute them perfectly.
              </p>
              <UButton size="xl" color="primary" variant="solid" class="px-8 py-4 text-lg" to="/dictionary">
                Open Dictionary
              </UButton>
            </div>
          </div>

          <div class="flex flex-col lg:flex-row items-center w-full gap-8 lg:gap-16">
            <UCard class="w-full lg:w-2/5 h-48 lg:h-72 flex flex-col items-center justify-center text-center shadow-lg hover:shadow-xl transition-shadow border-t-4 border-t-transparent hover:border-t-primary-500 duration-300">
              <UIcon name="i-lucide-brain" class="w-24 h-24 lg:w-40 lg:h-40 text-primary-500 mx-auto transition-colors duration-300" />
            </UCard>
            <div class="w-full lg:w-3/5 flex flex-col items-start text-left">
              <h2 class="text-3xl lg:text-5xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-4">
                Quiz
              </h2>
              <p class="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed text-justify">
                Test your skills. Frame your hands with the camera and complete the challenges 
                to consolidate your knowledge of sign language.
              </p>
              <UButton size="xl" color="primary" variant="solid" class="px-8 py-4 text-lg" to="/quiz">
                Start Quiz
              </UButton>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'

const { data: user, status } = useAuth()
const { startTour, isOnboardingActive } = useOnboarding()

// Usiamo un piccolo trick: controlliamo se l'utente esiste E se ha l'onboarding a false
onMounted(() => {
  // Se la sessione è già caricata quando si entra in homepage
  if (status.value === 'authenticated' && user.value?.has_completed_onboarding === false && !isOnboardingActive.value) {
    setTimeout(() => {
      startTour()
    }, 500)
  }
})

// Nel caso la richiesta /me ci metta un istante in più a caricare
watch(status, (newStatus) => {
  if (newStatus === 'authenticated' && user.value?.has_completed_onboarding === false && !isOnboardingActive.value) {
    setTimeout(() => {
      startTour()
    }, 500)
  }
})
</script>