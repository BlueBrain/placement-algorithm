function minBin = getMinBinModified (binsNB,binHeight,dendriteHeight,cType)
% returns the minimum possible bin number of neurons depending on the location of lower boundary

Layer = getLayerDefinition();

minBin = [];


%*********************defining the lower boundary

if strcmp (cType, 'L2PC') || strcmp (cType, 'L3PC')|| strcmp (cType,'L4PC')||strcmp (cType,'L5CSPC')|| strcmp (cType,'L5CHPC')
    lowerBoundary= (Layer(1).From + Layer(1).To)/2;
elseif strcmp (cType, 'L4SP')
    lowerBoundary = (Layer(3).From+Layer(3).To)/2;
else
    lowerBoundary=0;
end

dendriteHeight = dendriteHeight + binsNB * binHeight;

binIterator = 0;



while binIterator < binsNB

    dendriteHeight = dendriteHeight - binHeight; %start with neurons at last bin
    
    if dendriteHeight<lowerBoundary
        break
    end

    binIterator=binIterator+1;

end



minBin = binsNB-binIterator;


