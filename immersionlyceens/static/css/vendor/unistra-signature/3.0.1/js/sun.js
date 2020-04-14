document.addEventListener('DOMContentLoaded', function(event) {                                                               
  const sunContainers = document.querySelectorAll('.sun');                                                                    
  sunContainers.forEach(function(sunContainer) {                                                                              
    const links = sunContainer.querySelectorAll('a');                                                                         
    links.forEach(function(link) {                                                                                            
      const dataLink = link.attributes.href.nodeValue;                                                                        
      if (dataLink !== '#' && !link.classList.contains('sun-isolate')) {                                                      
        const filter = Array.prototype.filter,                                                                                
              linksWithSameHrefValue = filter.call(links, function(node) {                                                    
                return node !== link && node.attributes.href.nodeValue === dataLink && !node.classList.contains('sun-isolate');
              });                                                                                                             
        link.onmouseover = function(event) {                                                                                  
          linksWithSameHrefValue.forEach(function(linkWithSameHrefValue){                                                     
            linkWithSameHrefValue.classList.add('sun-hover');                                                                 
          });                                                                                                                 
        };                                                                                                                    
        link.onmouseout = function() {                                                                                        
          linksWithSameHrefValue.forEach(function(linkWithSameHrefValue){                                                     
            linkWithSameHrefValue.classList.remove('sun-hover');                                                              
          });                                                                                                                 
        };                                                                                                                    
      }                                                                                                                       
    });                                                                                                                       
  });                                                                                                                         
});