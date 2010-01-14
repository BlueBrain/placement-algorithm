function minBin = getMinBinModified_Sept30(binsNB,binHeight,dendriteHeight,axonHeight,cType, LayerFile)
% returns the minimum possible bin number of neurons depending on the location of lower boundary

Layer = getLayerDefinition(LayerFile);

minBin = [];


%*********************defining the lower boundary

if strcmp (cType, 'L2PC') || strcmp (cType, 'L3PC')|| strcmp (cType,'L4PC')||strcmp (cType,'L5CSPC')|| strcmp (cType,'L5CHPC')
    lowerBoundary= Layer(1).From;
elseif strcmp (cType, 'L4SP')
    lowerBoundary = Layer(3).From;
elseif strcmp (cType, 'MC')
    lowerBoundary = Layer(3).From;
else
    lowerBoundary=0;
end

if strcmp (cType, 'MC')
    minBin=(lowerBoundary-axonHeight)/(binsNB*binHeight);
if minBin<0
    minBin = 0;
elseif minBin>1
    minBin = 1;
end

else

minBin=(lowerBoundary-dendriteHeight)/(binsNB*binHeight);
if minBin<0
    minBin = 0;
elseif minBin>1
    minBin = 1;
end

end