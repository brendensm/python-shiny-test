// Create a file named 'www/lightbox.js' with this content
$(document).ready(function() {
  // Click handler for the guidelines image
  $(document).on('click', '#full_guidelines img, .clickable-image', function() {
    var imgSrc = $(this).attr('src');
    if (!imgSrc) {
      imgSrc = $(this).find('img').attr('src');
    }
    
    if (imgSrc) {
      $('#lightbox-img').attr('src', imgSrc);
      $('#lightbox').css('display', 'flex');
    }
  });
  
  // Close lightbox when clicking on the X or anywhere outside the image
  $(document).on('click', '.lightbox-close, .lightbox-overlay', function(e) {
    if (e.target === this) {
      $('#lightbox').css('display', 'none');
    }
  });
  
  // Prevent clicks on the image itself from closing the lightbox
  $(document).on('click', '.lightbox-content', function(e) {
    e.stopPropagation();
  });
});