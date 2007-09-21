function somaPositions = binPlacement(L,maxBin,binsNB,minBin)
% function that will return the positions of the somas, ie the bin 
% in which the neuron should be placed

counters=zeros(1,binsNB); %initialize all counters to zero

neuronsNB = length(maxBin); %all neurons in particular layer
somaPositions= zeros(1,neuronsNB);

rangeAllowed = [];
for q=1:binsNB 
  for j=1:neuronsNB %for each neuron
   
    rangeAllowed(j) = maxBin(j)-minBin(j)+1;
    c = ones(1,binsNB)* 1000;

    if minBin (j)~=-1
    if rangeAllowed(j)==q %start by placing the neurons with the smallest allowed range
    for z=minBin(j):maxBin(j) %go through all counters until reach maxBin
    c(z)= counters(z);
    end


  [r,i]= min(c); %i being the index of the smallest counter
  counters(i)=counters(i)+1;

  somaPositions(j)=i;
    end
   end
  end
end