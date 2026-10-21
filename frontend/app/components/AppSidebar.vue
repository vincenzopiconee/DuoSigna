<script setup>
import { ref, computed, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// --- LOGICA DI AUTENTICAZIONE ---
// Estraiamo anche "token" per poter fare chiamate sicure al backend!
const { data: authUser, signOut } = useAuth()

const userName = computed(() => authUser.value?.nome || 'Guest')
const userEmail = computed(() => authUser.value?.email || '')

// --- GESTIONE DELL'AVATAR ---
const currentAvatar = ref('https://api.dicebear.com/9.x/micah/svg?seed=Felix&backgroundColor=b6e3f4')

watchEffect(() => {
  if (authUser.value?.avatar_url) {
    currentAvatar.value = authUser.value.avatar_url
  }
})

const handleLogout = async () => {
  await signOut({ redirect: false }) 
  window.location.href = '/'
}

// ==============================================
// 1. STATO DELLA SIDEBAR
// ==============================================
const isSidebarOpen = useCookie('main-sidebar-open', { default: () => true })

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
  if (!isSidebarOpen.value) {
    isColorMenuOpen.value = false
  }
}

const isActive = (path) => route.path.startsWith(path)
const getBtnColor = (path) => isActive(path) ? 'primary' : 'gray'
const getBtnVariant = (path) => isActive(path) ? 'soft' : 'ghost'
const getBtnHoverClass = (path) => isActive(path) 
  ? '' 
  : 'hover:bg-primary-100 dark:hover:bg-primary-900/60 hover:text-primary-700 dark:hover:text-primary-300'

</script>

<template>
  <div 
    id="tour-main-sidebar"
    class="flex flex-col border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 transition-all duration-300 sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto overflow-x-hidden"
    :class="isSidebarOpen ? 'w-72 px-6 py-6' : 'w-20 px-2 py-6 items-center'"
  >
    <div class="flex flex-col w-full h-full">
      
      <UButton 
        :icon="isSidebarOpen ? 'i-lucide-panel-left-close' : 'i-lucide-panel-left-open'" 
        color="gray" 
        variant="ghost" 
        class="self-end mb-4 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
        :class="!isSidebarOpen ? 'self-center' : ''"
        @click="toggleSidebar" 
        aria-label="Toggle Sidebar"
      />

      <div class="flex flex-col items-center gap-4 mt-2">
        <UAvatar 
          :src="currentAvatar"
          alt="Profile Picture"
          :ui="{ rounded: 'rounded-full' }"
          class="shadow-lg border-4 border-white dark:border-gray-800 ring-2 ring-primary-500 dark:ring-primary-400 transition-all duration-300"
          :class="isSidebarOpen ? 'w-32 h-32' : 'w-12 h-12'"
        />
        <span v-if="isSidebarOpen" class="font-extrabold text-2xl text-gray-900 dark:text-white mt-2 tracking-tight">{{ userName }}</span>
      </div>

      <div class="flex flex-col gap-2 w-full mt-10">

        <UButton 
          icon="i-lucide-home" 
          :label="isSidebarOpen ? 'Homepage' : ''" 
          :color="getBtnColor('/homepage')" 
          :variant="getBtnVariant('/homepage')" 
          size="lg"
          class="text-base py-3 transition-all duration-200"
          :class="[isSidebarOpen ? 'justify-start px-4' : 'justify-center', getBtnHoverClass('/homepage')]" 
          to="/homepage"
        />
        
        <UButton 
          id="tour-sidebar-chatbot"
          icon="i-lucide-bot" 
          :label="isSidebarOpen ? 'Sign Tutor' : ''" 
          :color="getBtnColor('/chatbot')" 
          :variant="getBtnVariant('/chatbot')" 
          size="lg"
          class="text-base py-3 transition-all duration-200"
          :class="[isSidebarOpen ? 'justify-start px-4' : 'justify-center', getBtnHoverClass('/chatbot')]" 
          to="/chatbot"
        />

        <UButton 
          id="tour-sidebar-dictionary"
          icon="i-lucide-book-open" 
          :label="isSidebarOpen ? 'Dictionary' : ''" 
          :color="getBtnColor('/dictionary')" 
          :variant="getBtnVariant('/dictionary')" 
          size="lg"
          class="text-base py-3 transition-all duration-200"
          :class="[isSidebarOpen ? 'justify-start px-4' : 'justify-center', getBtnHoverClass('/dictionary')]" 
          to="/dictionary"
        />

        <UButton 
          id="tour-sidebar-quiz"
          icon="i-lucide-brain" 
          :label="isSidebarOpen ? 'Quiz' : ''" 
          :color="getBtnColor('/quiz')" 
          :variant="getBtnVariant('/quiz')" 
          size="lg"
          class="text-base py-3 transition-all duration-200"
          :class="[isSidebarOpen ? 'justify-start px-4' : 'justify-center', getBtnHoverClass('/quiz')]" 
          to="/quiz"
        />
        
        <UButton 
          icon="i-lucide-settings" 
          :label="isSidebarOpen ? 'Settings' : ''" 
          :color="getBtnColor('/settings')" 
          :variant="getBtnVariant('/settings')" 
          size="lg"
          class="text-base py-3 transition-all duration-200"
          :class="[isSidebarOpen ? 'justify-start px-4' : 'justify-center', getBtnHoverClass('/settings')]" 
          to="/settings"
        />

        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800 w-full">
          <UButton 
            icon="i-lucide-log-out" 
            :label="isSidebarOpen ? 'Logout' : ''" 
            color="red" 
            variant="ghost" 
            size="lg"
            class="w-full text-base py-3 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all duration-200" 
            :class="isSidebarOpen ? 'justify-start px-4' : 'justify-center'" 
            @click="handleLogout" 
          />
        </div>
      </div>
    </div>
  </div>
</template>