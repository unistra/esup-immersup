(function($) {

  $.fn.tdAnimateCSS = function(effect) {
    return this.each(function() {
      if($(this).isInViewport()) $(this).addClass(effect + ' animated')
    })
  }

})(jQuery)

jQuery(document).ready(function ($) {

  $('[data-toggle="tooltip"]').tooltip()

  $(window).on('load resize scroll', function () {
    $('.bg-parallax').each(function () {
      var windowTop = $(window).scrollTop()
      var speed = -$(this).data('scroll-speed')
      var topPosition = -(windowTop * speed) + 'px'
      $(this)
        .css(
          'background-position', 'top ' + topPosition + ' center'
        )
    })

    $('.bg-parallax-bottom').each(function () {
      var windowTop = $(window).scrollTop()
      var speed = -$(this).data('scroll-speed')
      var bottomPosition = (windowTop * speed) + 'px'
      $(this)
        .css(
          'background-position', 'bottom ' + bottomPosition + ' center'
        )
    })
  })


})
