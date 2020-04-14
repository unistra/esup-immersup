jQuery(document).ready(function ($) {
  // Hover effect for same links
  $('.sun').each(function () {
    var sun = $(this);
    var link = $(this).find('[href]');
    link.each(function () {
      var dataLink = $(this).attr('href');
      if (dataLink != '#') {
        sun.find('[href="' + dataLink + '"]:not(.sun-isolate)').hover(function () {
          sun.find('[href="' + dataLink + '"]:not(.sun-isolate)').addClass('sun-hover');
        }, function () {
          sun.find('[href="' + dataLink + '"]').removeClass('sun-hover');
        });
      }
    });
  });
});