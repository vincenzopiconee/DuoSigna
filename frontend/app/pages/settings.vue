<script setup>
import { ref, computed, watchEffect, onMounted } from 'vue'

// -- Auth & Profilo --
const { data: authUser, signOut, token, getSession } = useAuth()

const editName = ref('')
const editEmail = ref('')
const currentAvatar = ref('https://api.dicebear.com/9.x/micah/svg?seed=Felix&backgroundColor=b6e3f4')

watchEffect(() => {
  if (authUser.value) {
    if (authUser.value.nome) editName.value = authUser.value.nome
    if (authUser.value.email) editEmail.value = authUser.value.email
    if (authUser.value.avatar_url) currentAvatar.value = authUser.value.avatar_url
  }
})

// -- Stato Modali e Sezioni --
const isAvatarModalOpen = ref(false)
const isDeleteModalOpen = ref(false)
const showPasswordSection = ref(false)

const oldPassword = ref('')
const newPassword = ref('')
const passwordFeedback = ref({ message: '', type: '' })
const profileFeedback = ref({ message: '', type: '' })

const presetAvatars = [
  'https://api.dicebear.com/9.x/micah/svg?seed=Felix&backgroundColor=b6e3f4',
  'https://api.dicebear.com/9.x/micah/svg?seed=Aneka&backgroundColor=ffdfbf',
  'https://api.dicebear.com/9.x/micah/svg?seed=Milo&backgroundColor=c0aede',
  'https://api.dicebear.com/9.x/micah/svg?seed=Jude&backgroundColor=ffb5d2',
  'https://api.dicebear.com/9.x/micah/svg?seed=Leo&backgroundColor=fef08a',
  'https://api.dicebear.com/9.x/micah/svg?seed=Oliver&backgroundColor=ffd5dc',
  'https://api.dicebear.com/9.x/micah/svg?seed=Luna&backgroundColor=d1d4f9',
  'https://api.dicebear.com/9.x/micah/svg?seed=Kiki&backgroundColor=c0aede'
]

const selectAvatar = async (url) => {
  currentAvatar.value = url
  isAvatarModalOpen.value = false
  try {
    await $fetch('http://127.0.0.1:8000/update-avatar', {
      method: 'PUT',
      headers: { 'Authorization': token.value },
      body: { avatar_url: url }
    })
    if (authUser.value) authUser.value.avatar_url = url
  } catch (error) {
    console.error("Errore durante il salvataggio dell'avatar:", error)
  }
}

// -- Logica Profilo --
const isProfileChanged = computed(() => {
  return editName.value.trim() !== (authUser.value?.nome || '') ||
         editEmail.value.trim() !== (authUser.value?.email || '')
})

const handleSaveProfile = async () => {
  // 1. Controllo validità Email (deve contenere la @)
  if (!editEmail.value.includes('@')) {
    profileFeedback.value = { message: "Please enter a valid email address (must contain '@').", type: "error" }
    
    // RIMETTE I VALORI COME PRIMA
    if(authUser.value) {
      editName.value = authUser.value.nome || ''
      editEmail.value = authUser.value.email || ''
    }
    
    setTimeout(() => profileFeedback.value.message = '', 3000)
    return 
  }

  try {
    // 2. Chiamata PUT al backend
    await $fetch('http://127.0.0.1:8000/update-profile', {
      method: 'PUT',
      headers: { 'Authorization': token.value },
      body: {
        nome: editName.value.trim(),
        email: editEmail.value.trim()
      }
    })

    await getSession() 

    // 3. Successo
    profileFeedback.value = { message: "Profile updated successfully!", type: "success" }
    if(authUser.value) {
      authUser.value.nome = editName.value.trim()
      authUser.value.email = editEmail.value.trim()
    }
  } catch (error) {
    // ERRORE DAL SERVER (es. email già in uso)
    profileFeedback.value = { 
      message: error.data?.detail || "Error updating profile.", 
      type: "error" 
    }
    
    // RIMETTE I VALORI COME PRIMA
    if(authUser.value) {
      editName.value = authUser.value.nome || ''
      editEmail.value = authUser.value.email || ''
    }
  }
  
  setTimeout(() => profileFeedback.value.message = '', 3000)
}

// -- Logica Password --
const isPasswordFormValid = computed(() => {
  return oldPassword.value.length > 0 && newPassword.value.length > 0
})

const handleSavePassword = async () => {
  passwordFeedback.value = { message: '', type: '' }

  try {
    // Chiamata vera al backend
    await $fetch('http://127.0.0.1:8000/update-password', {
      method: 'PUT',
      headers: { 'Authorization': token.value },
      body: {
        old_password: oldPassword.value,
        new_password: newPassword.value
      }
    })

    // Se il backend risponde OK, svuota i campi e mostra il successo
    passwordFeedback.value = { message: "Password updated successfully!", type: "success" }
    oldPassword.value = ''
    newPassword.value = ''
    
  } catch (error) {
    // Se la vecchia password è errata, il backend lancia un errore che catturiamo qui
    passwordFeedback.value = { 
      message: error.data?.detail || "An error occurred.", 
      type: "error" 
    }
  }
  
  setTimeout(() => passwordFeedback.value.message = '', 3000)
}

const handleDeleteAccount = async () => {
  isDeleteModalOpen.value = false
  
  try {
    // 1. Diciamo al backend di eliminare tutto dal database
    await $fetch('http://127.0.0.1:8000/delete-account', {
      method: 'DELETE',
      headers: { 'Authorization': token.value }
    })
    
    // 2. Solo se il database l'ha eliminato, chiudiamo la sessione locale e torniamo al login
    await signOut({ redirect: false })
    window.location.href = '/'
    
  } catch (error) {
    console.error("Error during account deletion:", error)
    alert("An error occurred during deletion. Please try again.")
  }
}

// -- Temi e Aspetto --
const appConfig = useAppConfig()

const colorMode = useColorMode()

const selectedTheme = computed({
  get: () => colorMode.preference,
  set: (val) => { colorMode.preference = val }
})

const themeOptions = [
  { label: 'System', value: 'system' },
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' }
]

const themeColors = [
  { name: 'red', hex: '#ef4444' }, { name: 'orange', hex: '#f97316' }, { name: 'amber', hex: '#f59e0b' },
  { name: 'green', hex: '#22c55e' }, { name: 'emerald', hex: '#10b981' }, { name: 'teal', hex: '#14b8a6' },
  { name: 'cyan', hex: '#06b6d4' }, { name: 'blue', hex: '#3b82f6' }, { name: 'indigo', hex: '#6366f1' },
  { name: 'purple', hex: '#a855f7' }, { name: 'pink', hex: '#ec4899' }
]

const changeThemeColor = (colorName) => {
  appConfig.ui.colors.primary = colorName
  if (import.meta.client) {
    localStorage.setItem('duosigna-theme', colorName)
  }
}

onMounted(() => {
  const savedTheme = localStorage.getItem('duosigna-theme')
  if (savedTheme) {
    appConfig.ui.colors.primary = savedTheme
  }
})
</script>

<template>
  <div class="flex min-h-[calc(100vh-140px)] bg-gray-50 dark:bg-transparent transition-colors duration-200 w-full">
    <AppSidebar />
    
    <div class="flex-1 px-4 lg:px-8 py-8 w-full max-w-6xl mx-auto">
      
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm mb-8 flex items-center gap-4">
        <UIcon name="i-lucide-settings" class="w-8 h-8 text-primary-500" />
        <h1 class="text-3xl font-extrabold text-gray-900 dark:text-white">Settings & Profile</h1>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <div class="lg:col-span-1">
          <UCard class="w-full shadow-sm" :ui="{ body: 'p-6' }">
            <h2 class="text-xl font-bold mb-6 text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">Your Profile</h2>
            
            <div class="flex flex-col items-center">
              <div class="relative group cursor-pointer mb-6" @click="isAvatarModalOpen = true" title="Change Avatar">
                <UAvatar :src="currentAvatar" size="3xl" class="w-28 h-28 border-4 border-white dark:border-gray-800 shadow-lg ring-2 ring-transparent group-hover:ring-primary-500 transition-all" />
                <div class="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  <UIcon name="i-lucide-camera" class="w-8 h-8 text-white" />
                </div>
              </div>
              
              <div class="w-full flex flex-col gap-4 mb-4">
                <UInput v-model="editName" icon="i-lucide-user" class="w-full" input-class="font-bold text-gray-700 dark:text-gray-200" />
                <UInput v-model="editEmail" icon="i-lucide-mail" class="w-full" input-class="font-bold text-gray-700 dark:text-gray-200" />
              </div>
              
              <UButton 
                v-if="isProfileChanged"
                color="primary" 
                block 
                class="mb-2 shadow-md font-bold transition-all" 
                @click="handleSaveProfile"
              >
                Save Changes
              </UButton>
              <UButton 
                v-else
                color="gray" 
                variant="solid"
                block 
                disabled
                class="mb-2 font-bold opacity-50 cursor-not-allowed bg-gray-300 dark:bg-gray-800"
              >
                Save Changes
              </UButton>

              <div v-if="profileFeedback.message" :class="profileFeedback.type === 'error' ? 'text-red-500' : 'text-green-500'" class="text-sm font-bold text-center mb-4">
                {{ profileFeedback.message }}
              </div>
              
              <div class="w-full flex flex-col gap-3 border-t border-gray-200 dark:border-gray-800 pt-5 mt-2">
                
                <UButton 
                  color="gray" 
                  variant="ghost" 
                  block 
                  icon="i-lucide-key" 
                  @click="showPasswordSection = !showPasswordSection" 
                  class="font-semibold hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                >
                  Change Password
                </UButton>
                
                <transition name="slide-down">
                  <div v-if="showPasswordSection" class="flex flex-col gap-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800 my-2">
                    <UInput type="password" v-model="oldPassword" placeholder="Old Password" icon="i-lucide-unlock" />
                    <UInput type="password" v-model="newPassword" placeholder="New Password" icon="i-lucide-lock" />
                    
                    <div v-if="passwordFeedback.message" :class="passwordFeedback.type === 'error' ? 'text-red-500' : 'text-green-500'" class="text-sm font-bold text-center my-1 leading-tight">
                      {{ passwordFeedback.message }}
                    </div>

                    <UButton 
                      v-if="isPasswordFormValid"
                      color="primary" 
                      block 
                      class="mt-1 font-bold transition-colors" 
                      @click="handleSavePassword"
                    >
                      Update Password
                    </UButton>
                    <UButton 
                      v-else
                      color="gray" 
                      variant="solid"
                      block 
                      disabled
                      class="mt-1 font-bold opacity-50 cursor-not-allowed bg-gray-300 dark:bg-gray-800" 
                    >
                      Update Password
                    </UButton>
                  </div>
                </transition>

                <UButton 
                  icon="i-lucide-trash-2" 
                  class="font-bold mt-2 shadow-sm flex justify-center w-full bg-red-600 hover:bg-red-700 text-white dark:bg-red-600 dark:hover:bg-red-700 transition-colors" 
                  @click="isDeleteModalOpen = true"
                >
                  Delete Account
                </UButton>
              </div>
            </div>
          </UCard>
        </div>

        <div class="lg:col-span-2 space-y-8">
          <UCard class="w-full shadow-sm" :ui="{ body: 'p-6' }">
            <h2 class="text-xl font-bold mb-6 text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">Preferences</h2>
            
            <div class="space-y-8">
              <div>
                <h4 class="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Appearance & Customization</h4>
                <div class="flex flex-col gap-6">
                    
                  <div>
                    <span class="font-bold text-gray-700 dark:text-gray-200 block mb-3">Night Mode</span>
                    
                    <ClientOnly>
                      <div class="flex items-center gap-2 bg-gray-200/50 dark:bg-gray-800/50 p-1.5 rounded-xl w-fit border border-gray-200 dark:border-gray-700 shadow-sm">
                        <UButton 
                          :color="$colorMode.preference === 'system' ? 'primary' : 'gray'" 
                          :variant="$colorMode.preference === 'system' ? 'solid' : 'ghost'" 
                          icon="i-lucide-monitor" 
                          label="System" 
                          class="rounded-lg font-bold transition-all"
                          @click="$colorMode.preference = 'system'" 
                        />
                        <UButton 
                          :color="$colorMode.preference === 'light' ? 'primary' : 'gray'" 
                          :variant="$colorMode.preference === 'light' ? 'solid' : 'ghost'" 
                          icon="i-lucide-sun" 
                          label="Light" 
                          class="rounded-lg font-bold transition-all"
                          @click="$colorMode.preference = 'light'" 
                        />
                        <UButton 
                          :color="$colorMode.preference === 'dark' ? 'primary' : 'gray'" 
                          :variant="$colorMode.preference === 'dark' ? 'solid' : 'ghost'" 
                          icon="i-lucide-moon" 
                          label="Dark" 
                          class="rounded-lg font-bold transition-all"
                          @click="$colorMode.preference = 'dark'" 
                        />
                      </div>
                      
                      <template #fallback>
                        <div class="w-64 h-10 bg-gray-200 dark:bg-gray-800 animate-pulse rounded-xl"></div>
                      </template>
                    </ClientOnly>
                  </div>

                  <div>
                    <span class="font-bold text-gray-700 dark:text-gray-200 block mb-3">Theme Color</span>
                    <div class="flex flex-wrap gap-3">
                      <button v-for="color in themeColors" :key="color.name" 
                        class="w-8 h-8 rounded-full cursor-pointer transition-transform hover:scale-110 focus:outline-none shadow-sm"
                        :style="{ backgroundColor: color.hex }"
                        :class="appConfig.ui.colors.primary === color.name ? 'ring-2 ring-gray-900 dark:ring-white ring-offset-2 dark:ring-offset-gray-900 scale-125' : ''"
                        @click="changeThemeColor(color.name)" :title="color.name">
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </UCard>
        </div>

      </div>
    </div>

    <ClientOnly>
      <Teleport to="body">
        
        <transition name="modal-fade">
          <div v-if="isAvatarModalOpen" class="fixed inset-0 z-[999] flex items-center justify-center bg-gray-900/60 backdrop-blur-sm p-4" @click.self="isAvatarModalOpen = false">
            <UCard class="w-full max-w-md shadow-2xl relative">
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="text-xl font-bold">Choose Avatar</h3>
                  <UButton color="gray" variant="ghost" icon="i-lucide-x" class="-my-1" @click="isAvatarModalOpen = false" />
                </div>
              </template>
              <div class="flex flex-wrap justify-center gap-6 py-6">
                <div v-for="(url, idx) in presetAvatars" :key="idx" class="relative group cursor-pointer" @click="selectAvatar(url)">
                  <UAvatar :src="url" size="3xl" class="w-20 h-20 transition-transform hover:scale-110 border-4" :class="currentAvatar === url ? 'border-primary-500 scale-110' : 'border-transparent'" :ui="{ rounded: 'rounded-full' }" />
                </div>
              </div>
            </UCard>
          </div>
        </transition>

        <transition name="modal-fade">
          <div v-if="isDeleteModalOpen" class="fixed inset-0 z-[999] flex items-center justify-center bg-gray-900/60 backdrop-blur-sm p-4" @click.self="isDeleteModalOpen = false">
            <UCard class="w-full max-w-md shadow-2xl relative border-t-4 border-t-red-500">
              <template #header>
                <div class="flex items-center gap-2 text-red-500">
                  <UIcon name="i-lucide-alert-triangle" class="w-6 h-6" />
                  <h3 class="text-xl font-bold">Delete Account</h3>
                </div>
              </template>
              <div class="py-4">
                <p class="text-gray-600 dark:text-gray-300 font-medium leading-relaxed">
                  Are you sure you want to delete your account? This action is <b class="text-red-500">irreversible</b> and you will lose all your unlocked signs, score, and chat history.
                </p>
              </div>
              <template #footer>
                <div class="flex justify-end gap-3">
                  <UButton 
                    color="gray" 
                    variant="solid" 
                    class="px-4 py-2 font-bold shadow-sm bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 transition-colors"
                    @click="isDeleteModalOpen = false"
                  >
                    Cancel
                  </UButton>
                  
                  <UButton 
                    color="red" 
                    variant="solid" 
                    class="px-4 py-2 font-bold shadow-md bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 text-white transition-colors"
                    @click="handleDeleteAccount"
                  >
                    Yes, Delete Account
                  </UButton>
                </div>
              </template>
            </UCard>
          </div>
        </transition>

      </Teleport>
    </ClientOnly>
  </div>
</template>

<style scoped>
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.3s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; transform: scale(0.95); }

.slide-down-enter-active, .slide-down-leave-active { transition: all 0.3s ease; overflow: hidden; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; max-height: 0; margin-top: 0; padding-top: 0; padding-bottom: 0; }
.slide-down-enter-to, .slide-down-leave-from { opacity: 1; max-height: 250px; }
</style>