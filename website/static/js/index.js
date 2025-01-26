window.HELP_IMPROVE_VIDEOJS = false;


$(document).ready(function() {
    // Check for click events on the navbar burger icon

    var options = {
			slidesToScroll: 3,
			slidesToShow: 3,
			loop: true,
			infinite: true,
			autoplay: true,
			autoplaySpeed: 9999999,
			pagination: false,
    }

		// Initialize all div with carousel class
    var carousels = bulmaCarousel.attach('#iterative_writing', options);

	var option2 = {
		slidesToScroll: 1,
		slidesToShow: 1,
		loop: true,
		infinite: true,
		autoplay: true,
		autoplaySpeed: 9999999,
	}

	// Initialize all div with carousel class
var carousels = bulmaCarousel.attach('#motivation', option2);

	
    bulmaSlider.attach();


})
