%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function ind= location2(cLayerIndices, layerNB, cIndices, MPIndices)
%%returns indices of specific type in specific layer
      [tf, ind] = ismember(cIndices, cLayerIndices);
      minus= find(ind==0);
      ind(minus)=[];    
      