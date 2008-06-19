function maxBin= getMaxBinModified (binsNB,binHeight,maxHeight,dendriteHeight,cType)
% returns the maximum possible bin number of neurons depending on the location of upper boundary

Layer = getLayerDefinition();

%******************************defining upper boundary
if strcmp (cType, 'L4SP') || strcmp (cType, 'L6CTPC') || strcmp (cType,'L6CCPC')|| strcmp (cType,'L6CSPC')
    upperboundary = Layer(2).To;

else
    upperboundary = maxHeight;
end



%*************************************obtain maxBin
binIterator = 1;

while binIterator<=binsNB

    dendriteHeight=  dendriteHeight+binHeight;

    if dendriteHeight>upperboundary

        break;
    end
    binIterator = binIterator + 1;
end


if (binIterator==1)
    maxBin = binIterator;
else
    maxBin = binIterator-1;
end

