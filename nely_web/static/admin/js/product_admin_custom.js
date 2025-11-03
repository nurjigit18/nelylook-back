// static/admin/js/product_admin_custom.js

(function($) {
    $(document).ready(function() {
        
        // Add helper text to variants section
        var variantsTitle = $('#productvariant_set-group h2');
        if (variantsTitle.length) {
            variantsTitle.append(' <small style="color: #fff;">(Шаг 1: Добавьте цвета и размеры)</small>');
        }
        
        // Add helper text to images section
        var imagesTitle = $('#productimage_set-group h2');
        if (imagesTitle.length) {
            imagesTitle.append(' <small style="color: #856404;">(Шаг 2: Загрузите фото для каждого цвета)</small>');
        }
        
        // When color is selected in variant, show available colors for images
        $('#productvariant_set-group select[name$="-color"]').on('change', function() {
            updateAvailableColors();
        });
        
        // Function to update available colors in image inline
        function updateAvailableColors() {
            var selectedColors = [];
            
            // Collect all selected colors from variants
            $('#productvariant_set-group select[name$="-color"]').each(function() {
                var colorId = $(this).val();
                if (colorId) {
                    selectedColors.push(colorId);
                }
            });
            
            // Update color dropdowns in image inline
            $('#productimage_set-group select[name$="-color"]').each(function() {
                var imageColorSelect = $(this);
                var currentValue = imageColorSelect.val();
                
                // Filter options
                imageColorSelect.find('option').each(function() {
                    var option = $(this);
                    var optionValue = option.val();
                    
                    if (optionValue && selectedColors.indexOf(optionValue) === -1) {
                        option.hide().prop('disabled', true);
                    } else {
                        option.show().prop('disabled', false);
                    }
                });
                
                // If current value is not in selected colors, clear it
                if (currentValue && selectedColors.indexOf(currentValue) === -1) {
                    imageColorSelect.val('').trigger('change');
                }
            });
            
            // Show warning if no variants with colors
            if (selectedColors.length === 0) {
                if (!$('#color-warning').length) {
                    $('#productimage_set-group').prepend(
                        '<div id="color-warning" style="background: #f8d7da; color: #721c24; padding: 10px; margin-bottom: 10px; border: 1px solid #f5c6cb; border-radius: 4px;">' +
                        '⚠️ Сначала добавьте вариации с цветами ниже!' +
                        '</div>'
                    );
                }
            } else {
                $('#color-warning').remove();
            }
        }
        
        // Initial update
        updateAvailableColors();
        
        // Watch for new rows added (Django's dynamic formsets)
        if (typeof django !== 'undefined' && django.jQuery) {
            // Hook into Django's formset events
            $(document).on('formset:added', function(event, $row, formsetName) {
                if (formsetName === 'productvariant_set') {
                    updateAvailableColors();
                    
                    // Attach change handler to new color select
                    $row.find('select[name$="-color"]').on('change', updateAvailableColors);
                }
            });
        }
        
        // Add color indicator next to color selects
        function addColorIndicators() {
            $('select[name$="-color"]').each(function() {
                var select = $(this);
                
                // Skip if indicator already exists
                if (select.next('.color-indicator').length) return;
                
                var indicator = $('<span class="color-indicator" style="display: inline-block; width: 20px; height: 20px; margin-left: 10px; border: 1px solid #ccc; border-radius: 3px; vertical-align: middle;"></span>');
                select.after(indicator);
                
                function updateIndicator() {
                    var selectedOption = select.find('option:selected');
                    var colorCode = selectedOption.data('color-code');
                    
                    if (colorCode) {
                        indicator.css('background-color', colorCode).show();
                    } else {
                        indicator.hide();
                    }
                }
                
                select.on('change', updateIndicator);
                updateIndicator();
            });
        }
        
        addColorIndicators();
        
        // Validate before submit
        $('form').on('submit', function(e) {
            var hasVariants = $('#productvariant_set-group .has_original, #productvariant_set-group .dynamic-productvariant_set:visible').length > 0;
            var hasImages = $('#productimage_set-group .has_original, #productimage_set-group .dynamic-productimage_set:visible').length > 0;
            
            if (hasImages && !hasVariants) {
                alert('⚠️ Вы загрузили фото, но не добавили вариации! Сначала добавьте вариации с цветами и размерами.');
                e.preventDefault();
                return false;
            }
        });
        
        // Auto-scroll to errors
        if ($('.errorlist').length) {
            $('html, body').animate({
                scrollTop: $('.errorlist').first().offset().top - 100
            }, 500);
        }
    });
})(django.jQuery);