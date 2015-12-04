%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function minBinTemp= getMinBinnew (cType, ind, binsNB, dendriteHeights, binHeight)
% returns the minimum possible bin number of neurons depending on the location of lower boundary
  
Layer = getLayerDefinition();
   
    minBinTemp= [];
    k= binsNB;
    
    
    %*********************defining the lower boundary
   
      if strcmp (cType, 'L2PC') || strcmp (cType, 'L3PC')|| strcmp (cType,'L4PC')||strcmp (cType,'L5CSPC')|| strcmp (cType,'L5CHPC')
         lowerBoundary= Layer(1).From;            
         elseif strcmp (cType, 'L4SP')
             lowerBoundary = Layer(3).From;
      else
        lowerBoundary=0;            
      end 
   
     
    %*****************obtain minBin
    
    while k >=1

        dH = dendriteHeights+ k * binHeight; %start with neurons at last bin
        t = find(dH(ind)<lowerBoundary) ;    %constraint not satisfied
       
        
        if (~isempty(t))
            if (k==10)
                minBinTemp(ind(t)) = k;
            else
                minBinTemp(ind(t)) = k+1;
            end
            ind(t)=[]; %remove them from array
        end

        k=k-1;
        
    end
   
    minBinTemp(ind)=1; %all remaining can be placed in first bin
    
    
    