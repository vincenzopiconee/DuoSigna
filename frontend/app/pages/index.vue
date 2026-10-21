<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

// Inizializziamo il modulo di autenticazione e il router
const { signIn } = useAuth()
const router = useRouter()

const isLogin = ref(true)
const isLoading = ref(false)

// Variabili per messaggi di errore e successo dal database
const errorMessage = ref('')
const successMessage = ref('')

// Variabili per la gestione dell'immagine profilo
const selectedAvatarUrl = ref('')
const isAvatarModalOpen = ref(false)

// 5 immagini preimpostate tra cui scegliere
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

const loginFields = [
  { name: 'email', type: 'email', label: 'Email Address', placeholder: 'johndoe@email.com' },
  { name: 'password', type: 'password', label: 'Password', placeholder: '••••••••' }
]

const signupFields = [
  { name: 'name', type: 'text', label: 'Full Name', placeholder: 'John Doe' },
  { name: 'email', type: 'email', label: 'Email Address', placeholder: 'johndoe@email.com' },
  { name: 'password', type: 'password', label: 'Password', placeholder: 'Create a strong password' },
  { name: 'confirmPassword', type: 'password', label: 'Confirm Password', placeholder: 'Repeat your password' }
]

const currentFields = computed(() => isLogin.value ? loginFields : signupFields)

const toggleForm = () => {
  isLogin.value = !isLogin.value
  errorMessage.value = ''
  successMessage.value = ''
  if (isLogin.value) {
    selectedAvatarUrl.value = ''
  }
}

const selectAvatar = (url) => {
  selectedAvatarUrl.value = url
  isAvatarModalOpen.value = false
}

const handleSubmit = async (event) => {
  errorMessage.value = ''
  successMessage.value = ''

  // Estrattiamo i dati veri dal Form!
  const formData = event.data || {}

  // Ora usiamo formData per leggere i campi
  // 1. Validazione dei campi vuoti per Login e Registrazione
  if (isLogin.value) {
    if (!formData.email || !formData.password) {
      errorMessage.value = "All fields are required to log in."
      return
    }
  } else {
    if (!formData.name || !formData.email || !formData.password || !formData.confirmPassword) {
      errorMessage.value = "All fields are required to create an account."
      return
    }

    if (!selectedAvatarUrl.value) {
      errorMessage.value = "Please choose an avatar to complete your profile."
      return
    }
    
    // 2. Verifica corrispondenza password (già presente, ma spostata qui logicamente)
    if (formData.password !== formData.confirmPassword) {
      errorMessage.value = "Passwords do not match!"
      return
    }
  }
  
  isLoading.value = true
  
  try {
    if (isLogin.value) {
      // 1. GESTIONE LOGIN
      await signIn({
        email: formData.email,
        password: formData.password
      }, { callbackUrl: '/homepage' }) 
      
    } else {
      // 2. GESTIONE REGISTRAZIONE E LOGIN AUTOMATICO
      await $fetch('http://127.0.0.1:8000/register', {
        method: 'POST',
        body: {
          nome: formData.name, 
          email: formData.email,
          password: formData.password,
          avatar_url: selectedAvatarUrl.value
        }
      })
      
      // Se la registrazione va a buon fine, effettuiamo immediatamente il login
      // passando le stesse credenziali appena usate per registrarsi!
      await signIn({
        email: formData.email,
        password: formData.password
      }, { callbackUrl: '/homepage' })
    }
  } catch (err) {
    // Gestione degli errori (es. Email già esistente o Password errata)
    if (err.data && err.data.detail) {
      errorMessage.value = err.data.detail
    } else {
      errorMessage.value = "An error occurred. Please try again."
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div>
    <div class="min-h-[calc(100vh-140px)] flex items-start pt-16 lg:pt-28 bg-white dark:bg-transparent transition-colors duration-200">
      <div class="max-w-[1400px] mx-auto px-6 sm:px-8 md:px-12 w-full pb-12">
        
        <div class="flex flex-col lg:flex-row gap-16 lg:gap-24 xl:gap-32 items-start justify-between">
          
          <div class="w-full lg:w-3/5 flex flex-col items-center lg:mt-8">
            <div class="flex flex-col items-center mb-8">
              <div class="w-48 h-48 lg:w-56 lg:h-56 rounded-full overflow-hidden border-4 border-gray-100 dark:border-orange-400 shadow-md bg-white mb-6 flex-shrink-0">
                <img src="/logo.png" alt="Logo DuoSigna" class="w-full h-full object-cover" />
              </div>
              
              <h1 class="text-5xl lg:text-7xl font-extrabold text-gray-900 dark:text-white tracking-tight">
                DuoSigna
              </h1>
            </div>
            
            <p class="text-lg lg:text-xl text-gray-600 dark:text-gray-400 leading-relaxed max-w-2xl text-center lg:text-left">
              Learn sign language with DuoSigna, the interactive platform for mastering sign language through 
              engaging lessons, real-time feedback, and a supportive community. Start your journey to fluency today!
            </p>
          </div>

          <div class="w-full lg:w-2/5 flex justify-center">
            <UCard class="w-full max-w-md shadow-xl overflow-hidden transition-all duration-300" :ui="{ body: 'p-8 relative' }">
              
              <transition name="form-fade" mode="out-in">
                <div :key="isLogin ? 'login' : 'signup'">
                  
                  <div class="text-center mb-6">
                    <UIcon 
                      :name="isLogin ? 'i-lucide-log-in' : 'i-lucide-user-plus'" 
                      class="w-16 h-16 text-green-500 mx-auto mb-4" 
                    />
                    <h1 class="text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-2">
                      {{ isLogin ? 'Welcome back!' : 'Create an Account' }}
                    </h1>
                    <p class="text-gray-500 dark:text-gray-400 text-sm">
                      {{ isLogin ? 'Access your account to continue learning sign language.' : 'Join DuoSigna and start your journey to fluency.' }}
                    </p>
                  </div>

                  <div v-if="!isLogin" class="flex flex-col items-center justify-center mb-8">
                    <div 
                      class="relative group cursor-pointer" 
                      @click="isAvatarModalOpen = true"
                      title="Choose an avatar"
                    >
                      <UAvatar
                        :src="selectedAvatarUrl || null"
                        :icon="!selectedAvatarUrl ? 'i-lucide-user' : null"
                        size="3xl"
                        class="w-24 h-24 border-2 border-dashed border-gray-300 dark:border-gray-600 group-hover:border-primary-500 dark:group-hover:border-primary-400 transition-colors bg-gray-100 dark:bg-gray-800"
                        :ui="{ rounded: 'rounded-full' }"
                      />
                      <div class="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                        <UIcon name="i-lucide-image" class="w-8 h-8 text-white" />
                      </div>
                    </div>
                    <span class="text-sm font-medium text-gray-500 dark:text-gray-400 mt-3">
                      {{ selectedAvatarUrl ? 'Change Avatar' : 'Choose an Avatar' }}
                    </span>
                  </div>

                  <UAuthForm
                    :fields="currentFields"
                    :submit-button="{ label: 'Continue', loading: isLoading, color: 'green', variant: 'solid', size: 'lg' }"
                    @submit="handleSubmit"
                  >
                    <template #password-hint v-if="isLogin">
                      <button type="button" class="text-sm text-green-500 hover:underline">
                        Forgot password?
                      </button>
                    </template>

                    <template #validation>
                      <div v-if="errorMessage" class="text-red-500 text-sm text-center font-medium mb-2">
                        {{ errorMessage }}
                      </div>
                      <div v-if="successMessage" class="text-green-500 text-sm text-center font-medium mb-2">
                        {{ successMessage }}
                      </div>
                    </template>
                    <template #footer>
                      <div class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
                        {{ isLogin ? "Don't have an account?" : "Already have an account?" }}
                        <button 
                          type="button" 
                          @click="toggleForm" 
                          class="text-green-500 font-semibold hover:underline ml-1"
                        >
                          {{ isLogin ? 'Sign up here' : 'Login here' }}
                        </button>
                      </div>
                    </template>
                  </UAuthForm>
                </div>
              </transition>

            </UCard>
          </div>

        </div>
      </div>
    </div>

    <ClientOnly>
      <Teleport to="body">
        <transition name="modal-fade">
          <div 
            v-if="isAvatarModalOpen" 
            class="fixed inset-0 z-[999] flex items-center justify-center bg-gray-900/60 backdrop-blur-sm p-4 sm:p-6"
            @click.self="isAvatarModalOpen = false"
          >
            <UCard class="w-full max-w-md shadow-2xl relative" :ui="{ ring: '', divide: 'divide-y divide-gray-100 dark:divide-gray-800' }">
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="text-xl font-bold text-gray-900 dark:text-white">
                    Choose your Avatar
                  </h3>
                  <UButton color="gray" variant="ghost" icon="i-lucide-x" class="-my-1" @click="isAvatarModalOpen = false" />
                </div>
              </template>
              
              <div class="flex flex-wrap justify-center gap-6 py-6">
                <div 
                  v-for="(avatarUrl, index) in presetAvatars" 
                  :key="index"
                  class="relative group cursor-pointer"
                  @click="selectAvatar(avatarUrl)"
                >
                  <UAvatar
                    :src="avatarUrl"
                    size="3xl"
                    class="w-20 h-20 transition-transform duration-200 group-hover:scale-110 border-4"
                    :class="selectedAvatarUrl === avatarUrl ? 'border-primary-500 shadow-lg scale-110' : 'border-transparent hover:border-primary-300'"
                    :ui="{ rounded: 'rounded-full' }"
                  />
                  <div v-if="selectedAvatarUrl === avatarUrl" class="absolute -top-2 -right-2 bg-primary-500 text-white rounded-full p-1 shadow-md">
                    <UIcon name="i-lucide-check" class="w-4 h-4" />
                  </div>
                </div>
              </div>
            </UCard>
          </div>
        </transition>
      </Teleport>
    </ClientOnly>
  </div>
</template>

<style scoped>
/* Transizione laterale incrociata per il form */
.form-fade-enter-active,
.form-fade-leave-active {
  transition: all 0.25s ease-in-out;
}
.form-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.form-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* Transizione di dissolvenza per il modale custom */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>