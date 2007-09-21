function txt = myupdatefcntwo(empt,event_obj,MPIndices,neuronName,dcm_obj,plotIndex,reOrdering,wiS)
%allows displaying name of cell after clicking on a point in figure, used
%for figure with multiple simultaneous plots

dI = get(event_obj,'DataIndex');
info_struct = getCursorInfo(dcm_obj);
pI = find( wiS == info_struct.Target);
if pI ==1 
trueIndex = dI;
else
trueIndex = sum(plotIndex(1:(pI-1)))+dI;
end

trueIndex = reOrdering(trueIndex);

%MPIndices(trueIndex)

if (ismember(info_struct.Target, wiS))
txt = ['Name: ', neuronName(MPIndices(trueIndex))];
else
txt= ['not assigned'];
end