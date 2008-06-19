function belowC= belowConstraintNeuronsDnew (minBin,  maxHeightDendrite, neuronName,NeuronDB)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% identifies neurons with dendrites that do not reach their respective lower boundary
% format of output file: name   layer   mType    difference
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

disp('**********************below constraint:************************')
Layer = getLayerDefinition();





%initialize
pI=[];

% get info needed from neuronDB file
fid = fopen(NeuronDB);

A= textscan(fid,'%s%d%s%s%s');

neuron = A{1,1};
layerNB = A{1,2};
mType = A{1,3};
eType = A{1,4};
MEfilename = A{1,5};
fclose(fid);

neuronTypes = unique(mType);

tNB= length(neuronTypes);


% write on output file the name, layer and mType of neurones that do not satisfy the constraint
% indicate by how much the axone is above the constraint
fid = fopen('belowConstraintDNeuronDB.txt','wt');

counter=0;  %keeps track of te number of neurons below thei constraint

for i=1:tNB
    % current mType
    cType = neuronTypes{i};
    cTypeIndices =strmatch(cType,mType,'exact');
   
    
    if isempty(cTypeIndices)
        TEXT = sprintf(' ****************The are no cells defined as %s ****************',cType);
        disp(TEXT)
        continue
    end

    L= length (cTypeIndices);
    MPIndices= getMorphIndices(cTypeIndices, neuron, neuronName);

    %%%%%%%%%%%%%%%%%%%%%%%%%%define lower boundary%%%%%%%%%%%%%%%%%%%%

    if strcmp (cType, 'L2PC') || strcmp (cType, 'L3PC')|| strcmp (cType,'L4PC')||strcmp (cType,'L5CSPC')|| strcmp (cType,'L5CHPC')
        lowerBoundary= (Layer(1).From + Layer(1).To)/2;
    elseif strcmp (cType, 'L4SP')
        lowerBoundary = (Layer(3).From+Layer(3).To)/2;
    else
        lowerBoundary=0;
    end
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    for k=1:L
        cIndex = cTypeIndices(k);

        if minBin(cTypeIndices(k))>=0
            %dendrite reach:
            pI(k) = (minBin(cTypeIndices(k))) *(Layer(layerNB(cTypeIndices(k))).To-Layer(layerNB(cTypeIndices(k))).From)/10 + Layer(layerNB(cTypeIndices(k))).From + maxHeightDendrite(MPIndices(k));
            difference(k) =pI(k)- lowerBoundary;

            if (difference(k)<0)
                fprintf(fid,'%s\t%d\t%s\t%.2f\n',neuron{cIndex},layerNB(cIndex),mType{cIndex},difference(k));
                fprintf(1,'%s\t%d\t%s\t%.2f\n',neuron{cIndex},layerNB(cIndex),mType{cIndex},difference(k));
                belowC(cIndex)=cIndex;
                counter = counter +1;
            end
        else
            disp('negative minBin')
        end
    end

end

%no neurons are below their lower boundary
if counter==0
    belowC=-1;
end

fclose(fid)