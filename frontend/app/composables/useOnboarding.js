// composables/useOnboarding.js
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useState } from '#app'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'

export const useOnboarding = () => {
  const router = useRouter()
  const isOnboardingActive = useState('onboardingActive', () => false)
  const { token, data: user } = useAuth() 
  let driverObj = null

  const markTourAsCompleted = async () => {
    try {
      // 1. Diciamo al backend che il tour è finito
      await $fetch('http://127.0.0.1:8000/complete-onboarding', {
        method: 'POST',
        headers: { 'Authorization': token.value }
      })
      
      // 2. MODIFICA QUI: Aggiorniamo l'utente localmente anziché chiamare getSession()
      if (user.value) {
        user.value.has_completed_onboarding = true
      }
      
    } catch (error) {
      console.error("Error in saving the onboarding completion:", error)
    }
  }

  // Timer aumentato a 500ms per dare tempo a Vue di montare il DOM in tranquillità
  const routeAndWait = async (path, action, targetSelector) => {
    await router.push(path)
    
    let attempts = 0
    const checkExist = setInterval(() => {
      attempts++
      const el = document.querySelector(targetSelector)
      
      // Se l'elemento esiste ed è visibile sullo schermo...
      if (el && el.offsetParent !== null) {
        clearInterval(checkExist)
        setTimeout(() => { action() }, 150) // Micro-pausa per far finire le animazioni CSS
      } 
      // Fallback di sicurezza: dopo 2 secondi (20 tentativi), procedi comunque
      else if (attempts >= 20) { 
        clearInterval(checkExist)
        action()
      }
    }, 100) // Controlla ogni 100ms
  }

  // --- LOGICA BLOCCO SCHERMO CON SCUDO INVISIBILE ---
  const addTourLock = () => {
    // 1. CSS per disabilitare la selezione e disarmare l'elemento attivo
    if (!document.getElementById('tour-style-lock')) {
      const style = document.createElement('style')
      style.id = 'tour-style-lock'
      style.innerHTML = `
        body { overflow: hidden !important; user-select: none !important; }
        .driver-active-element, .driver-active-element * { pointer-events: none !important; }
        
        /* Forme, ombre e transizioni base (i colori li diamo con Tailwind) */
        .custom-driver-popover .driver-popover-footer button {
          border-radius: 0.75rem !important; 
          font-weight: 700 !important;       
          padding: 0.5rem 1.25rem !important;
          text-shadow: none !important;
          box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        }

        .custom-driver-popover .driver-popover-next-btn:hover {
          transform: scale(1.05);               
        }
      `
      document.head.appendChild(style)
    }

    //2. Un div trasparente che cattura tutti i click
    // Z-index alto per coprire l'app, ma inferiore a Driver.js (che viaggia su 1000000+)
    if (!document.getElementById('tour-invisible-shield')) {
      const shield = document.createElement('div')
      shield.id = 'tour-invisible-shield'
      shield.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 100000; background: transparent; cursor: not-allowed;'
      document.body.appendChild(shield)
    }
    
    // Togliamo il focus da qualsiasi elemento (es. se l'utente aveva già cliccato l'input)
    if (document.activeElement) {
      document.activeElement.blur()
    }
  }

  const removeTourLock = () => {
    const style = document.getElementById('tour-style-lock')
    if (style) style.remove()
    
    const shield = document.getElementById('tour-invisible-shield')
    if (shield) shield.remove()
  }
  // --------------------------------

  const startTour = () => {
    isOnboardingActive.value = true
    addTourLock() 
    
    driverObj = driver({
      showProgress: true,
      allowClose: false, 
      allowKeyboardControl: true, 
      stagePadding: 8,
      stageRadius: 16,
      popoverClass: 'custom-driver-popover',
      showButtons: ['next', 'previous', 'close'], 

      nextBtnText: 'Next',
      prevBtnText: 'Previous',

      onPopoverRender: () => {
        // Assegna le classi Tailwind dinamiche al bottone "Next"
        const nextBtn = document.querySelector('.driver-popover-next-btn');
        if (nextBtn) {
          nextBtn.classList.add('!bg-primary-500', 'hover:!bg-primary-600', '!text-white', '!border-none');
        }
        
        // Assegna le classi Tailwind al bottone "Previous" (inclusa la dark mode)
        const prevBtn = document.querySelector('.driver-popover-prev-btn');
        if (prevBtn) {
          prevBtn.classList.add(
            '!bg-gray-100', 'hover:!bg-gray-200', '!text-gray-600', '!border', '!border-gray-200', 
            'dark:!bg-gray-800', 'dark:!text-gray-300', 'dark:!border-gray-700', 'dark:hover:!bg-gray-700'
          );
        }
      },
      
      onDestroyed: () => {
        isOnboardingActive.value = false
        removeTourLock() 
        markTourAsCompleted()
      },
      
      steps: [
        { 
          element: '#tour-welcome-card', 
          popover: { 
            title: 'Welcome to DuoSigna', 
            description: 'Welcome to DuoSigna! Here you will be able to learn and practice American Sign Language.', 
            side: 'bottom',
            align: 'start',
            onNextClick: () => routeAndWait('/chatbot', () => driverObj.moveNext(), '#tour-chat-input')
          }
        },
        { 
          element: '#tour-chat-input', 
          popover: { 
            title: 'Sign Tutor', 
            description: 'Your Sign Tutor. Ask any curiosity you have about ASL or how to perform any sign, you will receive instant feedback and reference videos and you will be able to practice in front of the webcam.', 
            side: 'top', 
            align: 'center',
            onNextClick: () => routeAndWait('/dictionary', () => driverObj.moveNext(), '#tour-dictionary-header'),
            onPrevClick: () => routeAndWait('/homepage', () => driverObj.movePrevious(), '#tour-welcome-card')
          }
        },
        {
          element: '#tour-dictionary-header', 
          popover: {
            title: 'Dictionary',
            description: 'Here you will find all the signs organized by categories. Click on the unlocked cards to see their detailed instructions and reference GIFs, or unlock new ones by learning them with the Sign Tutor.',
            side: 'bottom',
            align: 'start',
            onNextClick: () => routeAndWait('/quiz', () => driverObj.moveNext(), '#tour-quiz-header'),
            onPrevClick: () => routeAndWait('/chatbot', () => driverObj.movePrevious(), '#tour-chat-input')
          }
        },
        {
          element: '#tour-quiz-header',
          popover: {
            title: 'Quiz',
            description: 'Test your skills! Choose categories and solve the quiz to see how well you know the signs.',
            side: 'bottom',
            align: 'start',
            onNextClick: () => routeAndWait('/homepage', () => driverObj.moveNext(), '#tour-main-sidebar'),
            onPrevClick: () => routeAndWait('/dictionary', () => driverObj.movePrevious(), '#tour-dictionary-header')
          }
        },
        {
          element: '#tour-main-sidebar',
          popover: {
            title: 'Quick Navigation',
            description: 'Use this lateral sidebar to quickly move between different pages of the application at any time.',
            side: 'right',
            align: 'center',
            onNextClick: () => driverObj.moveNext(), 
            onPrevClick: () => routeAndWait('/quiz', () => driverObj.movePrevious(), '#tour-quiz-header')
          }
        },
        {
          popoverClass: 'custom-driver-popover w-full !max-w-md',
          popover: {
            title: '<div class="text-center text-3xl font-black text-primary-500 mb-3">Ready?</div>',
            description: `
              <div class="flex flex-col items-center justify-center text-center">
                <p class="text-base text-gray-600 dark:text-gray-300 mb-5">You are all set! We are so <b>HAPPY</b> to have you here.</p>
                <div class="w-full bg-gray-50 dark:bg-gray-900 rounded-xl p-4 border border-gray-200 dark:border-gray-800 shadow-inner mb-6 flex justify-center">
                  <img src="http://127.0.0.1:8000/gif_output/rickroll.gif" alt="Happy Sign" class="h-48 object-contain rounded-lg" />
                </div>
                <p class="text-xl font-bold text-gray-800 dark:text-white uppercase tracking-widest">Happy Learning!</p>
              </div>
            `,
            onPrevClick: () => routeAndWait('/homepage', () => driverObj.movePrevious(), '#tour-main-sidebar')
          }
        }
      ]
    })

    routeAndWait('/homepage', () => driverObj.drive(), '#tour-welcome-card')
  }

  const stopTour = () => {
    if (driverObj) {
      driverObj.destroy()
    }
  }

  return { startTour, stopTour, isOnboardingActive }
}