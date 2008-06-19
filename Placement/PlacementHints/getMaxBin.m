function maxBinTemp= getMaxBin (cType, binsNB, dendriteHeights, binHeight, remainingIndices, maxHeight)
% returns the maximum possible bin number of neurons depending on the location of upper boundary

Layer = getLayerDefinition();

%******************************defining upper boundary
if strcmp (cType, 'L4SP')| strcmp (cType, 'L6CTPC')| strcmp (cType,'L6CCPC')| strcmp (cType,'L6CSPC')
    upperboundary = Layer(2).To;

else
    upperboundary = maxHeight;
end


%*************************************obtain maxBin
for k=1:binsNB

    dendriteHeights=  dendriteHeights+binHeight;
    t = find(dendriteHeights(remainingIndices)>upperboundary); %constraint not satisfied
    if (k==1)
        maxBinTemp(remainingIndices(t)) = k;
    else
        maxBinTemp(remainingIndices(t)) = k-1;
    end
    remainingIndices(t)=[]; %remove them from array
end


maxBinTemp(remainingIndices)=binsNB; %all remaining can be placed in last bin