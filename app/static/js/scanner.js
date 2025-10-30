document.addEventListener('DOMContentLoaded', function () {
    console.log("Scanner.js cargado.");

    // Elementos de la UI
    const resultContainer = document.getElementById('scan-result');
    const resultMessage = document.getElementById('result-message');
    const studentDetails = document.getElementById('student-details');
    const doorSelect = document.getElementById('door-select');
    const csrfToken = document.getElementById('csrf_token').value;

    // Sonidos de feedback
    const audioSuccess = new Audio('/static/audio/success.mp3');
    const audioError = new Audio('/static/audio/error.mp3');
    const studentPhoto = document.getElementById('student-photo');
    const photoPlaceholder = document.getElementById('photo-placeholder');

    // Función para mostrar el resultado final en la UI
    function showResult(success, message, details = '', photoUrl = null) {
        resultContainer.classList.remove('hidden', 'bg-green-100', 'text-green-800', 'bg-red-100', 'text-red-800', 'bg-yellow-100', 'text-yellow-800');
    
        
        if (success) {
            resultContainer.classList.add('bg-green-100', 'text-green-800');
            audioSuccess.play();
        } else {
            resultContainer.classList.add('bg-red-100', 'text-red-800');
            audioError.play();
        }
        
        resultMessage.textContent = message;
        studentDetails.textContent = details;
        // --- LÓGICA DE FOTO MEJORADA Y COMPLETA ---
        if (success && photoUrl) {
            // Caso 1: Éxito y HAY foto
            // Mostramos la imagen y ocultamos el placeholder
            studentPhoto.src = photoUrl;
            studentPhoto.classList.remove('hidden');
            photoPlaceholder.classList.add('hidden');
            // Cambiamos el color del borde de la imagen para que coincida con el fondo de éxito
            studentPhoto.classList.remove('border-transparent', 'border-red-500');
            studentPhoto.classList.add('border-green-500');

        } else {
            // Caso 2: Error o Éxito pero NO hay foto
            // Ocultamos la imagen y mostramos el placeholder
            studentPhoto.classList.add('hidden');
            photoPlaceholder.classList.remove('hidden');
        }

        // Ocultar todo después de 5 segundos y resetear al estado inicial
        setTimeout(() => {
            resultContainer.classList.add('hidden');
            studentPhoto.classList.add('hidden');
            photoPlaceholder.classList.remove('hidden'); // Dejar el placeholder visible para el próximo escaneo
        }, 5000);
    }

    // Función que se ejecuta cuando se escanea un QR exitosamente
    const onScanSuccess = (decodedText, decodedResult) => {
        // Pausar el escáner para evitar lecturas múltiples
        html5QrCode.pause();

        let studentId;
        try {
            const qrData = JSON.parse(decodedText);
            studentId = qrData.id;
            if (!studentId) throw new Error("ID no encontrado en el QR");
        } catch (e) {
            showResult(false, "Error: El formato del QR es inválido.");
            setTimeout(() => html5QrCode.resume(), 2000); // Reanudar después de un error
            return;
        }

        const selectedDoor = doorSelect.value;

        // --- ESTA ES LA PARTE CLAVE: ENVIAR DATOS AL SERVIDOR ---
        fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                student_id: studentId,
                door: selectedDoor
            })
        })
        .then(response => {
            if (!response.ok) {
                // Si la respuesta del servidor es un error (ej. 404, 403), capturarlo
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            // El servidor respondió con éxito (código 200)
            if (data.success) {
                const details = `Nombre: ${data.student.name} | Curso: ${data.student.course}`;
                showResult(true, data.message, details, data.student.photo_url);
            } else {
                // Esto podría ocurrir si el servidor devuelve success: false con un código 200
                showResult(false, data.message);
            }
        })
        .catch(errorData => {
            // Captura errores de red o errores de la respuesta del servidor (4xx, 5xx)
            console.error('Error en la solicitud fetch:', errorData);
            const message = errorData.message || "Error de conexión con el servidor.";
            showResult(false, message);
        })
        .finally(() => {
            // Reanudar el escáner después de 2 segundos, independientemente del resultado
            setTimeout(() => html5QrCode.resume(), 2000);
        });
    };

    // Función para mostrar mensajes de estado durante la inicialización
    function showStatus(message, isError = false) {
        console.log(`Estado: ${message}`);
        resultMessage.textContent = message;
        resultContainer.classList.remove('hidden', 'bg-green-100', 'text-green-800');
        if (isError) {
            resultContainer.classList.add('bg-red-100', 'text-red-800');
        } else {
            resultContainer.classList.add('bg-yellow-100', 'text-yellow-800');
        }
    }

    // --- Lógica de inicialización de la cámara ---
    const html5QrCode = new Html5Qrcode("qr-reader");

    Html5Qrcode.getCameras().then(cameras => {
        if (cameras && cameras.length) {
            const cameraId = cameras[cameras.length - 1].id; // Priorizar cámara trasera
            showStatus("Iniciando cámara...");

            html5QrCode.start(
                cameraId,
                { fps: 10, qrbox: { width: 250, height: 250 } },
                onScanSuccess,
                (errorMessage) => { /* No hacer nada en fallos de lectura */ }
            ).then(() => {
                // Ocultar el mensaje de "Iniciando cámara" una vez que el video está activo
                resultContainer.classList.add('hidden');
            }).catch(err => {
                showStatus(`Error al iniciar la cámara: ${err.message}`, true);
            });
        } else {
            showStatus("No se encontró ninguna cámara en este dispositivo.", true);
        }
    }).catch(err => {
        showStatus(`No se pudo obtener la lista de cámaras: ${err.message}`, true);
    });
});