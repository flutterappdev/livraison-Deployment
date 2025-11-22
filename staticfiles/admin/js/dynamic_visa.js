(function($) {
    $(document).ready(function() {
        var locationSelect = $('#id_location');
        var visaSelect = $('#id_visa');
        
        // Quand la localisation change
        locationSelect.change(function() {
            // Réinitialiser le visa
            visaSelect.val('');
            
            // Soumettre le formulaire
            $(this).closest('form').submit();
        });
    });
})(django.jQuery); 