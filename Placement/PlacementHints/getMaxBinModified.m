function maxBin= getMaxBinModified (binsNB,binHeight,maxHeight,dendriteHeight,axonHeight,cType)
% returns the maximum possible bin number of neurons depending on the location of upper boundary

%Layer = getLayerDefinition();
%
% %******************************defining upper boundary
% if strcmp (cType, 'L4SP') || strcmp (cType, 'L6CTPC') || strcmp (cType,'L6CCPC')|| strcmp (cType,'L6CSPC')
%     upperboundary = Layer(2).To;
%     constraint = dendriteHeight;    
% else
%     upperboundary = maxHeight;
%     constraint = max(dendriteHeight,axonHeight);
% end
% 

 upperboundary = maxHeight;
 constraint = max(dendriteHeight,axonHeight);
    
    
maxBin = (upperboundary-constraint)/(binHeight*binsNB);
if maxBin<0
    maxBin = 0;
elseif maxBin>1
    maxBin = 1;
end