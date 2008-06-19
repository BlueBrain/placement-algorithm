function MPIndices = getMorphIndices (cTypeIndices, neuron, neuronName)
% returns the corresponding index in the morphology file for any index in
% the neuronDB file

for k=1:length(cTypeIndices)
    cIndex = cTypeIndices(k);
    %current morpho Parameters Index

        MPIndices(k) = strmatch(neuron(cIndex),neuronName, 'exact');
    
end

