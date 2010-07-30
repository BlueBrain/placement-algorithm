function MPIndices = getMorphIndices (cTypeIndices, neuron, neuronName)
% returns the corresponding index in the morphology file for any index in
% the neuronDB file

%note that this re-sorts the morpology names each time the function is called, but we should only call this function
% once per layer.  If that becomes unacceptable, then the sorting should be done outside and the appropriate datastructure
% would get passed into the function in place of the neuronName array

h = java.util.Hashtable;

% using a java hashtable, store the morphology names as keys and the original index as the data for future search/retrieval
for k=1:length(neuronName)
    h.put( java.lang.String(neuronName(k)), java.lang.Integer(k) );
end

% for each neuron we are interested in finding, use hashtable.get func to retrieve the index of the original array and collect into an array
MPIndices = zeros(1, length(cTypeIndices));
for k=1:length(cTypeIndices)
    cIndex = cTypeIndices(k);
    %current morpho Parameters Index

    %MPIndices(k) = strmatch(neuron(cIndex),neuronName, 'exact');
    MPIndices(k) = h.get( java.lang.String(neuron(cIndex) ) );
end
